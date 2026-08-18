#include <x86intrin.h>
#include <cstdint>
#include <iostream>
#include <vector>

int main()
{
	unsigned int ui;

	uint64_t start_cycles = __rdtscp(&ui);

	int sum = 0;
	volatile int sink = 0;

	for (int i = 0; i < 1000; ++i)
	{
		sum += i;
		sink = sum;
	}

	uint64_t end_cycles = __rdtscp(&ui);

	(void)ui;
	(void)sink;

	std::cout << "Cycles elapsed: " << (end_cycles - start_cycles) << "\n";
	return 0;
}
