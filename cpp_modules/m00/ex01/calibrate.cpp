/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   calibrate.cpp                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: elsikira <elsikira@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/08/24 12:45:02 by elsikira          #+#    #+#             */
/*   Updated: 2026/08/25 13:08:42 by elsikira         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <cstdint>
#include <x86intrin.h>
#include <cstdio>
#include <chrono>
#include "timer.hpp"

using clk  = std::chrono::steady_clock;

static bool eq(const char *a, const char *b)
{
	int i;

	i = 0;
	while (a[i] && a[i] == b[i])
		i++;
	return (a[i] == b[i]);
}

double	tsc::calibrate(void)
{
	unsigned int	a0;
	unsigned int	a1;
	clk::time_point	c1;

	const clk::time_point	c0 = clk::now();
	const uint64_t			t0 = __rdtscp(&a0);
	_mm_lfence();
	const clk::time_point	end = c0 + std::chrono::milliseconds(100);

	while ((c1 = clk::now()) < end)
		;
	const uint64_t			t1 = __rdtscp(&a1);
	_mm_lfence();
	if (a0 != a1) //checks the core id using aux value when started, when stopped check again. if different, migration
				  //to a different piece of silicon while the clock was ticking :)
		std::printf("warning: migrated during calibration (use taskset)\n");
	const double			ns = std::chrono::duration<double, std::nano>(c1 - c0).count();
	tsc::g_ticks_per_ns = static_cast<double>(t1 - t0) / ns;
	return (tsc::g_ticks_per_ns);
}

int	main(void)
{
	char	w[256];
	double	base;
	bool	ctsc;
	bool	ntsc;
	FILE	*f;

	tsc::calibrate();
	std::printf("TSC freqency: %.3f GHz\n", tsc::g_ticks_per_ns);
	base = -1.0;
	ctsc = false;
	f = std::fopen("/proc/cpuinfo", "r");
	while (f && std::fscanf(f, "%255s", w) == 1)
	{
		if (eq(w, "constant_tsc"))
			ctsc = true;
		else if (eq(w, "nonstop_tsc"))
			ntsc = true;
		else if (eq(w, "@") && base < 0.0 && std::fscanf(f, "%255s", w) == 1)
			std::sscanf(w, "%lf", &base);
	}
	if (f)
		std::fclose(f);
	if (base > 0.0)
		std::printf("CPU base clock: %.3f GHz\n", base);
	else
		std::printf("CPU base clock: not advertised\n");
	std::printf("constant_tsc: %s nonstop_tsc: %s\n", ctsc ? "yes" : "no", ntsc ? "yes" : "no");
	return 0;
}
