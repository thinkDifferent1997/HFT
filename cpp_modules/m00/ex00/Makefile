# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: elsikira <elsikira@student.42.fr>          +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2026/08/22 16:39:44 by elsikira          #+#    #+#              #
#    Updated: 2026/08/22 16:50:06 by elsikira         ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME		= rdtsc

CXX			= c++

CXXFLAGS	= -Wall -Wextra -Werror -std=c++20 -O2

SRCS		= rdtsc.cpp
OBJS		= $(SRCS:.cpp=.o)

all:		$(NAME)

$(NAME):	$(OBJS)
			$(CXX) $(CXXFLAGS) -o $(NAME) $(OBJS)

%.o:		%.cpp
			$(CXX) $(CXXFLAGS) -c $< -o $@

clan:
			rm -f $(OBJS)

fclean:
			clean
			rm -f $(NAME)

re:			fclean all

.PHONY: all clean fclean re
