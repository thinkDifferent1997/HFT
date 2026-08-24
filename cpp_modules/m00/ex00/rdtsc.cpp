/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   rdtsc.cpp                                          :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: elsikira <elsikira@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/08/22 16:50:11 by elsikira          #+#    #+#             */
/*   Updated: 2026/08/22 17:34:28 by elsikira         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <cstdint>
#include <cstdio>
#include <x86intrin.h>

#define SAMPLES 1000
#define WARMUP 200

static uint64_t g_samples[SAMPLES];


static void sort(uint64_t *a, int n)
{

	for (int i = 1; i < n; i++)
	{
		uint64_t key = a[i];
		int j = i - 1;
		while (j >= 0 && a[j] > key)
		{
			a[j + 1] = a[j];
			j = j - 1;
		}
		a[j + 1] = key;
	}

}

static int measure(void)
{
	unsigned int	aux0;
	unsigned int	aux1;
	uint64_t		t0;
	uint64_t		t1;
	int				i;

	i = 0;
	while (i < WARMUP)
	{
		t0 = __rdtscp(&aux0);
		t1 = __rdtscp(&aux1);
		_mm_lfence(); //loads fence, forcing the processor to complete all prior memory load instructions 
					  //before executing any loads coming after in the program.
		i++;
	}
	i = 0;
	while (i < SAMPLES)
	{
		t0 = __rdtscp(&aux0);
		t1 = __rdtscp(&aux1);
		_mm_lfence();
		if (aux0 != aux1)
		{
			std::printf("MIGRATED\n");
			return (1);
		}
		g_samples[i] = t1 - t0;
		i++;
	}
	return (0);
}

int main(void)
{
	if (measure() != 0)
		return (1);

	sort(g_samples, SAMPLES);
	
	printf("rdtscp pair overhead: min=%lu median=%lu max=%lu ticks\n",
			g_samples[0],
			g_samples[SAMPLES / 2],
			g_samples[SAMPLES - 1]);

	return (0);
}
