#!/usr/bin/env python3
"""
TIER 1 — Live order book from a WebSocket feed.

This is deliberately Python, and deliberately not optimised. You are learning
the STATE MACHINE, not the performance. That comes later, in C++.

  pip install websockets requests
  python3 book.py

Verify the endpoints and the sync procedure against Binance's current API docs
before trusting this — exchange APIs change.

WHAT YOU ARE ACTUALLY LEARNING HERE:

  1. A live feed has no beginning. You connect mid-stream. Getting from
     "no idea" to "correct book" is the bootstrap problem.

  2. Messages carry sequence numbers. Gaps mean you missed something and your
     replica has silently diverged from reality.

  3. The book is not a data structure you fill in. It is a state machine you
     drive, one message at a time, forever.

All three of these are exactly the same on NASDAQ ITCH. Only the encoding
differs.
"""

import asyncio
import json
import time

import requests
import websockets

SYMBOL = "BTCUSDT"
# The plain "@depth" stream pushes about once per second — far too slow to
# fill a useful buffer. "@depth@100ms" gives ten times the resolution.
WS_URL = f"wss://stream.binance.com:9443/ws/{SYMBOL.lower()}@depth@100ms"
SNAPSHOT_URL = "https://api.binance.com/api/v3/depth"
DEPTH_SHOWN = 8


class OrderBook:
    """A price-level book. Maps price -> quantity for each side.

    This is MBP (market by price): sizes are aggregated, individual orders are
    invisible. NASDAQ ITCH is MBO (market by order) — you see every single
    order with its own ID. The state machine is the same shape; ITCH just has
    more moving parts.
    """

    def __init__(self):
        self.bids = {}          # price (float) -> quantity (float)
        self.asks = {}
        self.last_update_id = None
        self.applied = 0
        self.resyncs = 0

    def apply_side(self, side: dict, levels: list) -> None:
        for price_str, qty_str in levels:
            price = float(price_str)
            qty = float(qty_str)
            if qty == 0.0:
                # Quantity zero does NOT mean "a level with nothing at it".
                # It means DELETE THIS LEVEL. Getting this wrong leaves ghost
                # levels in your book and it will cross within minutes.
                side.pop(price, None)
            else:
                side[price] = qty

    def apply(self, event: dict) -> None:
        self.apply_side(self.bids, event.get("b", []))
        self.apply_side(self.asks, event.get("a", []))
        self.last_update_id = event["u"]
        self.applied += 1

    def load_snapshot(self, snap: dict) -> None:
        self.bids.clear()
        self.asks.clear()
        self.apply_side(self.bids, snap["bids"])
        self.apply_side(self.asks, snap["asks"])
        self.last_update_id = snap["lastUpdateId"]

    # --- invariants -------------------------------------------------------
    #
    # Run these constantly. A book that is silently wrong is worse than no
    # book, because you will trust it. In C++ these become assert() calls in
    # your debug build.

    def best_bid(self):
        return max(self.bids) if self.bids else None

    def best_ask(self):
        return min(self.asks) if self.asks else None

    def check(self) -> str | None:
        bid, ask = self.best_bid(), self.best_ask()
        if bid is not None and ask is not None and bid >= ask:
            return f"BOOK CROSSED: bid {bid} >= ask {ask}"
        if any(q <= 0 for q in self.bids.values()):
            return "non-positive quantity on bid side"
        if any(q <= 0 for q in self.asks.values()):
            return "non-positive quantity on ask side"
        return None

    def render(self) -> str:
        asks = sorted(self.asks.items())[:DEPTH_SHOWN][::-1] #8 cheapest sellers
        bids = sorted(self.bids.items(), reverse=True)[:DEPTH_SHOWN] #8 highest buyers

        lines = ["\033[2J\033[H"]      # clear screen, cursor home
        lines.append(f"  {SYMBOL}   applied={self.applied}  resyncs={self.resyncs}")
        lines.append(f"  seq={self.last_update_id}")
        lines.append("")
        lines.append(f"  {'PRICE':>14}  {'SIZE':>14}")
        lines.append("  " + "-" * 30)

        for price, qty in asks:
            lines.append(f"  {price:>14.2f}  {qty:>14.6f}   ask")

        bid, ask = self.best_bid(), self.best_ask()
        if bid is not None and ask is not None:
            lines.append(f"  {'':>14}  {'':>14}   <- spread {ask - bid:.2f}")
        else:
            lines.append("")

        for price, qty in bids:
            lines.append(f"  {price:>14.2f}  {qty:>14.6f}   bid")

        problem = self.check()
        if problem:
            lines.append("")
            lines.append(f"  !! {problem}")

        return "\n".join(lines)


def fetch_snapshot() -> dict:
    r = requests.get(SNAPSHOT_URL, params={"symbol": SYMBOL, "limit": 1000}, timeout=10)
    r.raise_for_status()
    return r.json()


async def run_once() -> None:
    """One full lifecycle: connect, bootstrap, stream until a gap appears.

    Returns normally when a gap is detected, so the caller can resync.
    """
    book = OrderBook()

    async with websockets.connect(WS_URL, ping_interval=20) as ws:
        print("connected, buffering while snapshot is in flight...")

        # STEP 1: request the snapshot IN THE BACKGROUND and keep draining the
        # socket the whole time it is in flight.
        #
        # THE CLASSIC BUG: buffer for a while, stop reading, THEN fetch the
        # snapshot. The REST round trip takes a few hundred milliseconds, and
        # every event during that window is lost. The snapshot then lands
        # newer than everything you buffered, with a hole in between, and the
        # book can never be built. Never stop reading the socket.
        loop = asyncio.get_running_loop()
        snap_future = loop.run_in_executor(None, fetch_snapshot)

        buffered = []
        while not snap_future.done():
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.1)
                buffered.append(json.loads(msg))
            except asyncio.TimeoutError:
                pass

        snap = await snap_future
        book.load_snapshot(snap)
        snap_id = snap["lastUpdateId"]
        print(f"snapshot id={snap_id}, buffered {len(buffered)} events")

        # STEP 2: discard events already reflected in the snapshot.
        pending = [e for e in buffered if e["u"] > snap_id]

        # STEP 3: if nothing buffered is newer than the snapshot, that is NOT
        # a failure — the snapshot is simply ahead of what we happened to
        # catch. The stream is continuous, so just keep reading: the next
        # event along must cover the snapshot's position.
        wait_until = time.time() + 15.0
        while not pending:
            if time.time() > wait_until:
                print("no event newer than the snapshot arrived; resyncing")
                return
            try:
                event = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            except asyncio.TimeoutError:
                continue
            if event["u"] > snap_id:
                pending.append(event)

        # STEP 4: the first surviving event must STRADDLE the snapshot. Its
        # range [U, u] has to contain snap_id + 1. If it starts past that, we
        # are genuinely missing updates and the book is unbuildable — resync.
        first = pending[0]
        if not (first["U"] <= snap_id + 1 <= first["u"]):
            print(f"real gap: snapshot ends at {snap_id}, first event covers "
                  f"{first['U']}..{first['u']}; resyncing")
            return

        for event in pending:
            book.apply(event)

        print("book synchronised. streaming...")
        await asyncio.sleep(0.4)

        # STEP 5: stream forever, verifying continuity on every message.
        last_render = 0.0
        async for raw in ws:
            event = json.loads(raw)

            # THE CHECK THAT MATTERS. Each event declares the range of updates
            # it carries. If it does not start exactly where the last one
            # ended, we missed something and our replica is now fiction.
            if event["U"] != book.last_update_id + 1:
                print(f"\nSEQUENCE GAP: expected {book.last_update_id + 1}, "
                      f"got {event['U']}. Book is stale. Resyncing.")
                return

            book.apply(event)

            problem = book.check()
            if problem:
                print(f"\nINVARIANT VIOLATED: {problem}")
                return

            now = time.time()
            if now - last_render > 0.25:
                print(book.render())
                last_render = now


async def main() -> None:
    resyncs = 0
    while True:
        try:
            await run_once()
        except (websockets.WebSocketException, requests.RequestException) as e:
            print(f"\nconnection problem: {e}")
        resyncs += 1
        print(f"resync #{resyncs} in 2s...")
        await asyncio.sleep(2.0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
