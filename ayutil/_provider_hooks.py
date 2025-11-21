import importlib
from collections.abc import Callable
from types import NoneType

from ayutil.generics import ProviderSpec,provider_factory
from ayutil.generics._provider_decorators import MISSING

if importlib.util.find_spec('aiohttp'):
    from aiohttp import ClientSession,TCPConnector


    def generic_aiohttp_client(connector=None,headers=None):
        
        if connector is None:connector=TCPConnector(limit=100, limit_per_host=10, force_close=True, enable_cleanup_closed=True)
        #Often the connector can stall/get stuck if you want to close the connection, without force close and cleanup.
        if headers is None: headers = {
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (compatible; Anonymous;)",
        "DNT": "1"} #generic "please don't track and keep me connected".
        #also
        #timeout=aiohttp.ClientTimeout(total=30)
        #for spotty connections might help.
        
        return ClientSession(connector=connector, headers=headers, raise_for_status=True)
    
    
    class _AioHttp(ProviderSpec):
        
        aio_client:ClientSession = None  # for easy check
        
        @classmethod
        def init(cls,client:ClientSession|NoneType=None):
            if cls.aio_client is None:
                if client is None:
                    cls.aio_client = generic_aiohttp_client()
                else:
                    cls.aio_client = client
    
        @classmethod
        async def replace(cls, client:ClientSession|NoneType=None):
            if cls.aio_client is not None: await cls.aio_client.close()
            if client is None: cls.aio_client = generic_aiohttp_client()
            else: cls.aio_client = client
        
        #--- Override Fields ---
        def call(self,client:ClientSession|NoneType=None):
            self.init(client) #might as well
            return self.aio_client
        #This is actually unecessary, as call and provider_type will never be called until the first call of a decorated function
        #Making it protected from premature instantiation of a ClientSession, eg before a running event loop. 
        def provider_type(self): return ClientSession
        
    #Use aio_provider.init(ClientSession()) after event loop startup
    aio_provider=_AioHttp(provider_kwargs=('aio_client',))
    #use setter: aio_provider.provider_kwargs=('your_http_kwargname',) this can be after this provider is instantiated here, and after the event loop. ofc decorator and factory overrides still work.
    
    aiohttp_client=provider_factory(aio_provider)

#For the async postgres library it isn't uncommon to have multiple connections to different databases, and that requires multiple 
#different objects.
#so this implementation does not use a global/class level session.

if importlib.util.find_spec('asyncpg'):
    import asyncpg as apg

    class ProvideApgPool(ProviderSpec):
    
        @property
        def pool(self):
            return self._provider_value
    
        async def open(self):
            await self.pool
    
        async def close(self):
            await self.pool.expire_connections()
            await self.pool.close()
        
        async def replace(self, pool: apg.Pool):
            #a safe way to replace a connection, if that is needed for the provider
            if self._provider_value is not MISSING and not self._provider_value._isclosed:
                await self.close()
            self._provider_value=pool
            await self.open() #we wait to open the new connection, as it won't do it implicitly
        
        #for anything else use pool_provider.pool.
        
        #--- Override Fields ---
        def call(self):
            return self.pool
        #This is actually unecessary, as call and provider_type will never be called until the first call of a decorated function
        #Making it protected from premature instantiation of a ClientSession, eg before a running event loop. 
        def provider_type(self): return apg.Pool
        
        
    def asyncpgpool_decoratorandprovider(pool:apg.Pool,provider_kwargs=('apg_pool',))->tuple[Callable,ProvideApgPool]:
        pool_provider=ProvideApgPool(pool,provider_kwargs=provider_kwargs)
        #as this is from a synchronous call, use pool_provider.open() at env launch time. or you can just 
        # async with pool:
        # within the scope of the first decorated functions,
        return provider_factory(pool_provider),pool_provider
