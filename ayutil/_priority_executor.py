from concurrent import futures
import asyncio as aio
import itertools
from functools import partial


_ct=itertools.count()

_executor_pqueue:dict[futures.Executor,aio.PriorityQueue]={}

def priority_execute(executor:futures.Executor, task, *args, priority:int=0):
    "Execute tasks in an executor as they come in, ordered first by priority then sequentially."
    #print(f"Executor ID: {id(executor)}")
    if executor not in _executor_pqueue:
        _executor_pqueue[executor] = aio.PriorityQueue()
        aio.create_task(_run_priority_queue(executor))

    loop = aio.get_event_loop()
    future = loop.create_future()

    #print(f"Inserting Future ID: {id(future)} into queue")

    _executor_pqueue[executor].put_nowait((priority,next(_ct), future, task, args))
    #print('Current queue lineup 1',list(_executor_pqueue[executor]._queue))

    return aio.ensure_future(future)

def _callback(f, fut, sem):
    try:
        #if not fut.done():  # Which should be never
        if f.exception() is not None:
            fut.set_exception(f.exception())
            #print(f'Exception occurred in future. Future ID: {id(fut)}, Exception: {fut.exception()}, Cancelled: {fut.cancelled()}')
        else:
            fut.set_result(f.result())
            #print(f'Setting future result. Future ID: {id(fut)}, Result: {fut.result()}, Cancelled: {fut.cancelled()}')
        #else:
            #print(f'Future was done, this shouldnt happen. Future ID: {id(fut)}, Result: {fut.result()}, Cancelled: {fut.cancelled()}')
    except Exception as e:
        print(f"Exception in _callback: {e}")
    finally:
        #print('Released sem')
        sem.release()

async def _run_priority_queue(executor:futures.ThreadPoolExecutor):
    loop=aio.get_running_loop()
    pqueue=_executor_pqueue[executor]
    workers = executor.__dict__.get('num_workers',1)
    sem=aio.Semaphore(workers)
    while True:
        _,_, future, task, args = await pqueue.get()
        #print(f"Recieved Future ID: {id(future)} from queue")
        loop.run_in_executor(executor, task, *args).add_done_callback(partial(_callback,fut=future,sem=sem))
        await sem.acquire()
        #print('Current queue lineup 2', list(_executor_pqueue[executor]._queue))

def clear_pqueue():
    """WARNING: Only run when you are certain there are no more tasks to be completed. In a normal situation
    where few new executors are being created, you should never have to call this."""
    _executor_pqueue.clear()
