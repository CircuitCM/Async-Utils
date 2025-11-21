import asyncio as aio
from typing import Union
import time as t
import warnings


async def _r_delay(afunc,delay:float):
    await aio.sleep(delay)
    return await afunc
#--- all functions below return what ever completes first

async def completion_funnel(gen:aiter,timeout=None):
    """
    As tasks come in from the parallel generator they will launch, simultaneously yielding whatever is completed.
    The parallel version of 'aio.as_completed'.
    """
    done = aio.queues.Queue()
    cont = [True,]
    todo=set()

    def _on_completion(f):
        if not todo:
            return  # _on_timeout() was here first.
        todo.remove(f)
        done.put_nowait(f)
        if not todo and timeout_handle is not None:
            timeout_handle.cancel()

    def _on_timeout():
        for f in todo:
            f.remove_done_callback(_on_completion)
            done.put_nowait(None)  # Queue a dummy value for _wait_for_one().
        todo.clear()

    async def g():
        async for f in gen:
            ft = aio.ensure_future(f)
            todo.add(ft)
            ft.add_done_callback(_on_completion)
        cont[0]=False
    aio.create_task(g())
    timeout_handle = None
    if timeout is not None:
        timeout_handle = aio.get_event_loop().call_later(timeout, _on_timeout)

    async def _wait_for_one():
        f = await done.get()
        if f is None:
            # Dummy value from _on_timeout().
            raise aio.exceptions.TimeoutError
        return f.result()  # May raise f.exception().

    while cont[0] or todo or not done.empty():
        #have to await these
        yield await _wait_for_one()


def deprecated(f):
    def g(*a, **k):
        warnings.warn(f.__name__ + " is deprecated",
                      DeprecationWarning, 2)
        return f(*a, **k)
    return g
     

@deprecated
def delayed_round_robin(gen:Union[aiter,iter],delay:float=0.1,batch:int=1,isasync:bool=True):
    '''
    Asynchronously delays execution of a stream in groups of `batch`. Can be used as a rate limiter for example.
    Rendered trivial by simply using a parallel queue as a congestion filter within the tasks fed to `completion_funnel`
    or `asyncio.as_completed`.
    '''
    if isasync:
        async def n(bt:int=batch):
            ti = 0.
            tm = t.time()
            async for g in gen:
                yield _r_delay(g, ti)
                bt-=1
                if bt==0:
                    bt=batch
                    tn = t.time()
                    ti += tm + delay*batch - tn
                    tm = tn
        return completion_funnel(n())
    else:
        bt=batch
        ti = 0.
        tm = t.time()
        ls =[]
        for g in gen:
            ls.append(_r_delay(g, ti))
            bt -= 1
            if bt == 0:
                bt = batch
                tn = t.time()
                ti += tm + delay * batch - tn
                tm = tn
        return aio.as_completed(ls)
