/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   timer.hpp                                          :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: elsikira <elsikira@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/08/24 12:51:50 by elsikira          #+#    #+#             */
/*   Updated: 2026/08/24 12:53:57 by elsikira         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef TIMER_HPP
# define TIMER_HPP

#include <cstdint>

namespace tsc
{
	inline double	g_ticks_per_ns = 0.0;
	double			calibrate(void);
	inline double	tsc_to_ns(uint64_t ticks)
	{
		return (static_cast<double>(ticks) / g_ticks_per_ns);
	}
}

#endif
