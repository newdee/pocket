# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    wrap_funcs.py                                      :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: dfine <coding@dfine.tech>                  +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/05/12 11:44:04 by dfine             #+#    #+#              #
#    Updated: 2025/05/12 11:44:05 by dfine            ###   ########.fr        #
#                                                                              #
# **************************************************************************** #
from collections.abc import Awaitable
from functools import wraps
from time import perf_counter
from typing import Callable, ParamSpec, TypeVar

from pocket.logger import logger

P = ParamSpec("P")
R = TypeVar("R")


def get_time_async(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    name = getattr(func, "__name__", func.__class__.__name__)

    @wraps(func)
    async def timed_execution(*args: P.args, **kwargs: P.kwargs) -> R:
        logger.info(f"Starting async func@{name} with {args= }, {kwargs= }")
        try:
            start_time = perf_counter()
            result = await func(*args, **kwargs)
            end_time = perf_counter()
            logger.info(f"{name} took {end_time - start_time:.3f}s")
            return result
        except Exception as e:
            logger.error(f"{name} failed with exception: {e}")
            raise

    return timed_execution


def get_time_sync(func: Callable[P, R]) -> Callable[P, R]:
    name = getattr(func, "__name__", func.__class__.__name__)

    @wraps(func)
    def timed_execution(*args: P.args, **kwargs: P.kwargs) -> R:
        logger.info(f"Starting sync func@{name} with {args= }, {kwargs= }")
        try:
            start_time = perf_counter()
            result = func(*args, **kwargs)
            end_time = perf_counter()
            logger.info(f"{name} took {end_time - start_time:.3f}s")
            return result
        except Exception as e:
            logger.error(f"{name} failed with exception: {e}")
            raise

    return timed_execution
