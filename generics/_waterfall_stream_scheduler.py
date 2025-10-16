import asyncio as aio
from warnings import deprecated


async def _shoot_yield(n:int, branchflow:aio.Queue, nbranchflow:aio.Queue, finished:list,num_branches:int):
    i = 0
    while not finished[n] or not branchflow.empty():
        i += 1
        #print('Waiting on ', 'Branch: ', i, ' Shoot: ', n + 1)
        branch = await branchflow.get()
        result = await branch.get()
        finished[n + 1] = i==num_branches
        nbranchflow.put_nowait(branch)
        #print('Branch: ', i, ' Shoot: ', n + 1, " Sent.")
        yield result, branch
    #finished[n + 1] = True
    #print('Shoot: ', n + 1, ' completed.')

def make_shoots(num_shoots:int,num_branches:int):
    """A system to guarantee ordering of results both per coroutine (branches) and in-coroutine (shoots) while making no restrictions on order of processing, and intrinsically notifying the running loop.
    Set up as async generators per `shoot`. """
    shoots = []
    finished = [False for _ in range(0, num_shoots+1)]
    branches = [aio.Queue() for _ in range(0, num_branches)]
    branchflow = aio.Queue()
    for i in branches:
        branchflow.put_nowait(i)
    finished[0] = True

    for n in range(0, num_shoots):
        nbranchflow = aio.Queue()
        shoots.append(_shoot_yield(n,branchflow,nbranchflow,finished,num_branches))
        branchflow = nbranchflow

    return shoots, branches

async def _sh(waitable, queue:aio.Queue):
    #print('shooting')
    fin = await waitable
    queue.put_nowait(fin)
    
def shoot_next(waitable, queue:aio.Queue):
    return aio.create_task(_sh(waitable,queue))
