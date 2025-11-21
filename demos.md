## Link Demo
The simplest way to think of this is it's just `asyncio.gather` but it doesn't crash by handing it sync functions or values, it instead returns them after evaluating all functions, coroutines, and awaitables, in the same order like gather:


```python
import ayutil as ayo
import asyncio as aio
import time as tm
async def st():
    await aio.sleep(.1)

await ayo.link(st,aio.sleep(.1),lambda : tm.sleep(.1),420)
```



    (None, None, None, 420)



```python
await aio.gather(st,aio.sleep(.1),lambda : tm.sleep(.1),420)
```

    TypeError: An asyncio.Future, a coroutine or an awaitable is required


## Completion Funnel
This is an extension of `asyncio.as_completed`, the difference being it accepts an async generator/iterator. Then it funnels new tasks in and returns results of the latest tasks simultaneously. While as_completed in reality turns it's iterator into a set and won't begin returning results until the iterator has been walked through once. This is similar to having a future manage it's own response state but instead relegated to a FIFO generator, providing some convenience and decoupling.


```python
import ayutil as ayo
import asyncio as aio
import random as rand

async def sl_random(rn=1,reself=True):
    ts=rand.random()
    await aio.sleep(ts)
    if reself:
        print(f'First Sleep Random {rn}: {ts}')
        return sl_random(rn,False)        
    else:
        print(f'Second Sleep Random {rn}: {ts}')
    
async def rn():
    for r in aio.as_completed((*(sl_random(i) for i in range(1,6)),)):
        yield await r
    
    
async for v in ayo.completion_funnel(rn(),):
    v
#completion funnel doesn't
```

    First Sleep Random 5: 0.05457654764012776
    First Sleep Random 4: 0.11663755112014795
    Second Sleep Random 4: 0.06786783001674146
    Second Sleep Random 5: 0.25522237389767455
    First Sleep Random 2: 0.5802584186618809
    First Sleep Random 1: 0.6747769889503964
    First Sleep Random 3: 0.7279575081064846
    Second Sleep Random 3: 0.21596820299079034
    Second Sleep Random 2: 0.3773827454186065
    Second Sleep Random 1: 0.606377026793165
    

## Waterfall Stream Scheduler

The waterfall stream scheduler restricts the execution of awaitables until a historical grid of dependencies is satisfied first. This gif demonstrates a somewhat realistic flow of tasks where there are streams (branches) and waterfalls (shoots).

    
![gif](grid_anim.gif)


The only dependency of this scheduler is that at a given yellow square along row i and column j, must have results returned for all $0$ to $i - 1$ rows and $0$ to $j$ columns. Note that tasks from the same row $i$ do **not** have to be processed first, this is somewhat demonstrated by the first row finishing simultaneously. This allows stream tasks to finish at unordered times but still provide ordered results, it's only this grid dependency that needs to be satisfied before the task is scheduled. The animation demonstrates a strict breadth first search starting at square/node (1,0), in a real setting all of row 1 may be scheduled (turn yellow) nearly simultaneously, corresponding with availability. This means that depending on how much concurrency and compute division is available, you will achieve the most throughput by sorting the processing stages from least to most time and assign them descending to each row.

### How to use:
We first set up the shoots

```python
from ayutil import shoot_next, make_brancheshoot
import asyncio as aio
import time as tm

branches, shoots = make_brancheshoot(4, 4)
# branches=queues
branches, shoots
```




    ([<async_generator object _shoot_yield at 0x00000208DA6569B0>,
      <async_generator object _shoot_yield at 0x00000208DA657340>,
      <async_generator object _shoot_yield at 0x00000208DA657120>,
      <async_generator object _shoot_yield at 0x00000208DA657670>],
     [<Queue at 0x208dabda9d0 maxsize=0>,
      <Queue at 0x208da6a3650 maxsize=0>,
      <Queue at 0x208da6a3810 maxsize=0>,
      <Queue at 0x208da6a1950 maxsize=0>])

```python
fc=1/len(shoots)

async def sleepnr(sl):
    ts=rand.random() if sl ==0. else sl
    await aio.sleep(ts)
    return ts
#sleepnr can represent any kind mini-batch processing framework such as (but no limited to):
#  Multi-core or multi-gpu contiguous memory or vector processing.
#  Improving the efficiency of LLM responses that require this context ordering.

async def gen_passthrough(ayiter:aiter, corofunc, branch=1, itime=0, verbose=True, nopass=False):
    br=1
    async for dly,q in ayiter:
        if not nopass:
            shoot_next(corofunc(0.),q)
        if verbose:print(f'Branch: {branch}, Shoot: {br}, Full Delay: {(tm.perf_counter() - itime):.5f}, Required Delay: {dly}')
        br+=1
#Depending on if you implement a generic gen_passthrough or separate ones for each depth layer
#You can also implement logic or delays within the iterator.

#sleep line 1, no dependencies but variable sleep delay for example. start
st=tm.perf_counter()

#sleepinit=aio.gather(*(shoot_next(sleepnr(0.),q) for q in shoots),)

(*(shoot_next(sleepnr(.01+i/3),q) for i,q in enumerate(shoots)),) #no need to await this one
sleep1=gen_passthrough(branches[0], sleepnr, 1, st, )
sleep2=gen_passthrough(branches[1], sleepnr, 2, st, )
sleep3=gen_passthrough(branches[2], sleepnr, 3, st, )
sleep4=gen_passthrough(branches[3], sleepnr, 4, st, nopass=True)
sleep1,sleep2,sleep3,sleep4=tuple(aio.ensure_future(sl) for sl in (sleep1,sleep2,sleep3,sleep4))
await sleep1
print(f"--- Round 1 Sleep completed in {tm.perf_counter()-st:.5f} seconds.")
await sleep2
print(f"--- Round 2 Sleep completed in {tm.perf_counter()-st:.5f} seconds.")
await sleep3
print(f"--- Round 3 Sleep completed in {tm.perf_counter()-st:.5f} seconds.")
await sleep4
print(f"--- Round 4 Sleep completed in {tm.perf_counter()-st:.5f} seconds.")
```

    Branch: 1, Shoot: 1, Full Delay: 0.01036, Required Delay: 0.01
    Branch: 1, Shoot: 2, Full Delay: 0.33807, Required Delay: 0.3433333333333333
    Branch: 2, Shoot: 1, Full Delay: 0.36461, Required Delay: 0.3542025315756381
    Branch: 1, Shoot: 3, Full Delay: 0.68131, Required Delay: 0.6766666666666666
    Branch: 2, Shoot: 2, Full Delay: 0.74969, Required Delay: 0.39553332496347837
    Branch: 3, Shoot: 1, Full Delay: 0.92434, Required Delay: 0.5643734465605241
    Branch: 1, Shoot: 4, Full Delay: 1.01295, Required Delay: 1.01
    Branch: 2, Shoot: 3, Full Delay: 1.01298, Required Delay: 0.3521166032838139
    --- Round 1 Sleep completed in 1.01308 seconds.
    Branch: 3, Shoot: 2, Full Delay: 1.19576, Required Delay: 0.44776559038899577
    Branch: 4, Shoot: 1, Full Delay: 1.34100, Required Delay: 0.4159671697523438
    Branch: 4, Shoot: 2, Full Delay: 1.34102, Required Delay: 0.11883272073555284
    Branch: 3, Shoot: 3, Full Delay: 1.44433, Required Delay: 0.43071370690332234
    Branch: 2, Shoot: 4, Full Delay: 1.61246, Required Delay: 0.5894272756328165
    --- Round 2 Sleep completed in 1.61258 seconds.
    Branch: 4, Shoot: 3, Full Delay: 1.79354, Required Delay: 0.3526312001473805
    Branch: 3, Shoot: 4, Full Delay: 1.99522, Required Delay: 0.38850934753887956
    --- Round 3 Sleep completed in 1.99539 seconds.
    Branch: 4, Shoot: 4, Full Delay: 2.53448, Required Delay: 0.5387543586544322
    --- Round 4 Sleep completed in 2.53466 seconds.
    

We see that the 2D dependency grid is satisfied.

### Provider Decorator for Static Dict - Demo


```python
from typing import List, Optional, Tuple, Collection
from ayutil.generics import provider_factory,ProviderSpec

#A global dict, we want the args of the dict to be the same, but don't care if it's modifiable
g_dict={1:'h',2:'l',5:'test'}

#multiple strategies
# 1.
class ProvideDict(ProviderSpec):
    #we use instance instead of class methods and parameters, for easier genericity.
    def call(self): return g_dict.copy() # as it shouldn't modify we dont need: global g_dict
    
Ps1=ProvideDict() #optional: provider_type=dict,provider_kwargs=('dic','dic1')
# 2.
Ps2=ProviderSpec(g_dict.copy(),provider_kwargs=('dic1','dic'))

d_prov1=provider_factory(Ps1,kwarg_names=('dic1','dic'))
d_prov2=provider_factory(Ps2)

#@d_prov1
def test_modify1(somt,somt1=5,dic1:dict=None):
    print(f'Test 1,{somt} dict before:',dic1)
    dic1[somt1]=somt
    print(f'Test 1,{somt} dict after:',dic1)

test_m1p1=d_prov1(test_modify1)
test_m1p2=d_prov2(test_modify1)

print('Calling decorated dict modification:')
test_m1p1(1,)
test_m1p2(2,)
print('global dict:',g_dict)
print('\nCalling test_m1p2 a second time:')
test_m1p2(3,)
print('global dict:',g_dict)

print('\nWithout decorators:')
def test_b(somt,somt1=5,dic1:dict=g_dict):
    print(f'Test b,{somt} dict before:',dic1)
    dic1[somt1]=somt
    print(f'Test b,{somt} dict after:',dic1)
test_b(1)
test_b(2)
print('global dict:',g_dict)


#Now if we want to change the object instance of global dict?
def chg_forp1():
    global g_dict
    g_dict={1:'l',2:'l',5:'test'} #all that is needed for our override class
    #note how we don't need to reference the provider instance.
    #if our type is not the same, eg we turn it into another collection, need to call:
    del Ps1.provider_type

def chg_forp2():
    global g_dict
    g_dict={1:'l',2:'l',5:'test'}
    Ps2.new_instance(g_dict.copy())
    #the difference between the first and second method boils down to a static reference or per object ref.
    
chg_forp1()
chg_forp2()
print('\nAfter Reset:')
test_m1p2(2,)
print('global dict:',g_dict)

@d_prov1('dic2')
def test_m2p1(somt,somt1=5,dic2:dict=None):
    print(f'Test 2,{somt} dict before:',dic2)
    dic2[somt1]=somt
    print(f'Test 2,{somt} dict after:',dic2)

print('\nDecorator with non-default kwarg spec:')
test_m2p1(1,)


class ProvideDict2(ProviderSpec):
    #we use instance instead of class methods and parameters, for easier genericity.
    def call(self): return g_dict.copy() # as it shouldn't modify we dont need: global g_dict
    def provider_type(self): return type(self()) #assuming it's cheap enough
    
#base class example:
class ProvideDict3(ProviderSpec):
    #we use instance instead of class methods and parameters, for easier genericity.
    def call(self): return g_dict.copy() # as it shouldn't modify we dont need: global g_dict
    def provider_type(self): return Collection

d_prov22=provider_factory(ProvideDict2(provider_kwargs=('dic1','dic')))
d_prov3=provider_factory(ProvideDict3(provider_kwargs=('dic1','dic')))

test_m1p22=d_prov22(test_modify1)
test_m1p3=d_prov3(test_modify1)

print('\nTest without type reset:')
test_m1p22(1,1)
test_m1p3(1,1)

g_dict=['h','l','test']
print('\nAfter changing collection type')
test_m1p22(1,1)
test_m1p3(1,1)
print('global list:',g_dict)


```

    Calling decorated dict modification:
    Test 1,1 dict before: {1: 'h', 2: 'l', 5: 'test'}
    Test 1,1 dict after: {1: 'h', 2: 'l', 5: 1}
    Test 1,2 dict before: {1: 'h', 2: 'l', 5: 'test'}
    Test 1,2 dict after: {1: 'h', 2: 'l', 5: 2}
    global dict: {1: 'h', 2: 'l', 5: 'test'}
    
    Calling test_m1p2 a second time:
    Test 1,3 dict before: {1: 'h', 2: 'l', 5: 2}
    Test 1,3 dict after: {1: 'h', 2: 'l', 5: 3}
    global dict: {1: 'h', 2: 'l', 5: 'test'}
    
    Without decorators:
    Test b,1 dict before: {1: 'h', 2: 'l', 5: 'test'}
    Test b,1 dict after: {1: 'h', 2: 'l', 5: 1}
    Test b,2 dict before: {1: 'h', 2: 'l', 5: 1}
    Test b,2 dict after: {1: 'h', 2: 'l', 5: 2}
    global dict: {1: 'h', 2: 'l', 5: 2}
    
    After Reset:
    Test 1,2 dict before: {1: 'l', 2: 'l', 5: 'test'}
    Test 1,2 dict after: {1: 'l', 2: 'l', 5: 2}
    global dict: {1: 'l', 2: 'l', 5: 'test'}
    
    Decorator with non-default kwarg spec:
    Test 2,1 dict before: {1: 'l', 2: 'l', 5: 'test'}
    Test 2,1 dict after: {1: 'l', 2: 'l', 5: 1}
    
    Test without type reset:
    Test 1,1 dict before: {1: 'l', 2: 'l', 5: 'test'}
    Test 1,1 dict after: {1: 1, 2: 'l', 5: 'test'}
    Test 1,1 dict before: {1: 'l', 2: 'l', 5: 'test'}
    Test 1,1 dict after: {1: 1, 2: 'l', 5: 'test'}
    
    After changing collection type
    Test 1,1 dict before: ['h', 'l', 'test']
    Test 1,1 dict after: ['h', 1, 'test']
    Test 1,1 dict before: ['h', 'l', 'test']
    Test 1,1 dict after: ['h', 1, 'test']
    global list: ['h', 'l', 'test']
    


```python

```
