from collections.abc import Callable, Awaitable
import asyncio as aio


async def link(*args, return_exceptions=True,sync_wait=True):
    """ Called `link` because it "links callables, awaitables, and neither" into a single return result statement.
    
    Takes a sequence of anything, runs the callables to get values or awaitables. If it's awaitable, assume it was a coroutinefunction in which case we await on these along with any others that were sent. """
    todo = {}
    def _prep(i, ar):
        # If it's a callable, evaluate
        if isinstance(ar, Callable):
            val = ar()
            # sync_wait: collect any Awaitable result
            # not sync_wait: only collect if the callable is a coroutine function
            if isinstance(val, Awaitable):
                #we expect iscoroutinefunction to always return a callable.
                if sync_wait or aio.iscoroutinefunction(ar):todo[i] = val
            return val
        # If the original arg is already an Awaitable, always collect it
        if isinstance(ar, Awaitable): todo[i] = ar
        return ar
    
    args = (*(_prep(i, ar) for i, ar in enumerate(args)),)

    if len(todo) > 0:
        fin = await aio.gather(*todo.values(), return_exceptions=return_exceptions)
        res = {i: res for i, res in zip(todo.keys(), fin)}
        nargs = (*(res.get(i,n) for i, n in enumerate(args)),)
        return nargs
    return args
