import asyncio as aio
from collections.abc import Awaitable,AsyncGenerator


async def _shoot_yield(n:int, branchflow:aio.Queue, nbranchflow:aio.Queue, finished:list,num_branches:int):
    i = 0
    while not finished[n] or not branchflow.empty():
        i += 1
        #print('Waiting on ', 'Branch: ', i, ' Shoot: ', n + 1)
        shoot = await branchflow.get()
        result = await shoot.get()
        finished[n + 1] = i==num_branches
        nbranchflow.put_nowait(shoot)
        #print('Branch: ', i, ' Shoot: ', n + 1, " Sent.")
        yield result, shoot
    #finished[n + 1] = True
    #print('Shoot: ', n + 1, ' completed.')

def make_brancheshoot(num_branches:int, num_shoots:int)->tuple[list[AsyncGenerator],list[aio.Queue]]:
    """A system to guarantee ordering of results both per coroutine (shoots) and in-coroutine (branches) while making no restrictions on order of processing, and intrinsically notifying the running loop.
    Set up as async generators per `branch`. """
    branches = []
    finished = [False for _ in range(0, num_branches + 1)]
    shoots = [aio.Queue() for _ in range(0, num_shoots)]
    branchflow = aio.Queue()
    for i in shoots:
        branchflow.put_nowait(i)
    finished[0] = True

    for n in range(0, num_branches):
        nbranchflow = aio.Queue()
        branches.append(_shoot_yield(n, branchflow, nbranchflow, finished, num_shoots))
        branchflow = nbranchflow

    return branches, shoots

async def _sh(waitable, queue:aio.Queue):
    #print('shooting')
    fin = await waitable
    queue.put_nowait(fin)
    
def shoot_next(waitable, queue:aio.Queue):
    return aio.create_task(_sh(waitable,queue))
