from ._completion_funnel import completion_funnel, delayed_round_robin
from ._priority_executor import priority_execute, clear_pqueue
from ._waterfall_stream_scheduler import shoot_next, make_brancheshoot
from .generics import link

import importlib
if importlib.util.find_spec('aiohttp'):
    from ._provider_hooks import generic_aiohttp_client,aiohttp_client,aio_provider

if importlib.util.find_spec('asynpg'):
    from ._provider_hooks import asyncpgpool_decoratorandprovider,ProvideApgPool
