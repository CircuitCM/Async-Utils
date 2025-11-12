from collections.abc import Callable, Awaitable
import asyncio as aio

async def link(*args,return_exceptions=True):
    # it's redundant to evaluate sync functions here so it assumes all callables hold awaitables.
    todo={i:arg() if isinstance(arg,Callable) else arg for i,arg in enumerate(args) if isinstance(arg,(Callable,Awaitable))}
    if len(todo)>0:
        fin=await aio.gather(*todo.values(),return_exceptions=return_exceptions)
        res={i:res for i,res in zip(todo.keys(),fin)}
        nargs=(*(res[i] if i in res else n for i,n in enumerate(args)),)
        return nargs
    return args
