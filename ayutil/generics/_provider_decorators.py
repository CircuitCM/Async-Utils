# Fix the module by rewriting _get_value with proper 'nonlocal' placement, then rerun tests.
from textwrap import dedent

from functools import wraps
import asyncio as aio
import inspect
from typing import Any, Callable, Optional, Sequence, Tuple, Union

class _Missing:
    pass
MISSING = _Missing()


# The callable provider that handles sending the object we want through our decorators.
# Originally meant to be a basic callable for returning the object instance, identifiable out of other callables.
# as our object provision could be a callable itself.
# but it was extended slightly to support, base/inherited types, and overriding fields.
class ProviderSpec:
    """
    Inheritable helper: subclass this and implement either `call(self, ...)` or
    `__call__(self, ...)` to produce the shared value. The base class lazily
    infers and caches `_share_type` on first use. You may also set
    `share_kwargs` to provide default kwarg names.
    """

    # _share_type: Any = MISSING
    # share_kwargs: Optional[Union[str, Sequence[str]]] = None
    
    def __init__(self,provider_value=MISSING,provider_type=MISSING,provider_kwargs=None):
        self._provider_value=provider_value
        self._provider_type: Any = provider_type
        self.provider_kwargs: Optional[Union[str, Sequence[str]]] = provider_kwargs
        
    def call(self, *args, **kwargs):  # optional override point
        return self._provider_value

    def __call__(self, *args, **kwargs):  # default dispatch to `call`
        return self.call(*args, **kwargs)

    @property
    def provider_type(self):
        if self._provider_type is MISSING:
            vl = self() #if we have made it to this point, assume call is producing non-MISSING.
            self._provider_type = type(vl)
        return self._provider_type

    @provider_type.setter
    def provider_type(self, p_type):
        self._provider_type = p_type

    @provider_type.deleter
    def provider_type(self):
        self._provider_type = MISSING
    
    def new_instance(self,value):
        self._provider_value = value
        del self.provider_type
    


def provider_factory(
        source: Union[Any, ProviderSpec],
        value_type: Any = MISSING,
        kwarg_names: Optional[Union[str, Sequence[str]]] = None,
):
    # we use a provider spec instead of a generic callable, incase already callable.
    isp = isinstance(source,ProviderSpec)
    if not isp: # its a value type provider spec so build that
        spec = ProviderSpec(source,value_type,kwarg_names)
    else:
        _iv = value_type is MISSING
        _kwspc=not isinstance(kwarg_names,(str,Sequence))
        if _iv and _kwspc: #we fully rely on the provider spec, no need to mess with it
            spec=source
        else:
            spec = ProviderSpec()
            #source call to allow user to change value object/instance
            spec.call = source.call #... hmm otherwise self lambda
            #if specified value type in factory, override, source spec
            spec.provider_type=source.provider_type if _iv else value_type
            #if override kwarg names:
            spec.provider_kwargs=source.provider_kwargs if _kwspc else kwarg_names

    # --- core decoration logic, per-function --------------------------------
    
    def _decorate(func, ovr_names: str|Sequence[str]):
        is_async_gen = inspect.isasyncgenfunction(func)
        is_gen = inspect.isgeneratorfunction(func)
        is_coro = aio.iscoroutinefunction(func)
        # injection core
        def _ij_chk(args, kwargs):
            # If we have a resolved type, check the last positional arg and candidate kwargs
            tp=spec.provider_type
            kw = ovr_names if ovr_names else spec.provider_kwargs
            #print('kw',kw)
            
            if tp is MISSING:
                for key in kw:
                    if key in kwargs: #a key was found, but because we don't know the type, we assume it's valid.
                        return False,key
                #we don't have it's type and if ckey is -1 we know there wasn't a matching kwarg
                #So we assume the last arg needs injection.
                return True,kw[0] if kw else -1
            else:
                if args:
                    last = args[-1]
                    try:
                        if isinstance(last, tp):
                            return False,-1
                    except Exception:
                        pass
                fkey=None
                for key in kw:
                    if key in kwargs:
                        if fkey is None:fkey = key
                        try: #this should return the first matching key where the types are different.
                            if isinstance(kwargs[key], tp):
                                return False,key
                        except Exception:
                            pass
                lt=len(kw)>0
                #print('fkey',fkey)
                return True,kw[0] if lt and fkey is None else fkey if lt else -1#we do not want it 

        def _build_call(args, kwargs,iid=-1):
            # decide how to provide the value
            value = spec()
            if iid==-1:
                return (*args, value), kwargs
            else: #for clarity we will always assign the key if there is one, this is still compatible with the
                #required parameters portion of the signature, if the last req param has the same name as iid.
                return args,{iid: value, **kwargs}

        if is_async_gen:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                inj, iid = _ij_chk(args, kwargs)
                if inj:
                    args, kwargs = _build_call(args, kwargs, iid=iid)
                async for item in func(*args, **kwargs):
                    yield item

        elif is_coro:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                inj, iid = _ij_chk(args, kwargs)
                if inj:
                    args, kwargs = _build_call(args, kwargs, iid=iid)
                return await func(*args, **kwargs)

        elif is_gen:
            @wraps(func)
            def wrapper(*args, **kwargs):
                inj, iid = _ij_chk(args, kwargs)
                if inj:
                    args, kwargs = _build_call(args, kwargs, iid=iid)
                for item in func(*args, **kwargs):
                    yield item

        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                inj, iid = _ij_chk(args, kwargs)
                if inj:
                    args, kwargs = _build_call(args, kwargs, iid=iid)
                return func(*args, **kwargs)

        return wrapper
    
    # --- the returned decorator (supports override names) -------------------
    def _decorator_entry(*maybe_names):
        # If used bare: first arg is the function to decorate and there are no overrides
        if len(maybe_names) == 1 and callable(maybe_names[0]) and not isinstance(maybe_names[0], str):
            func = maybe_names[0]
            override_names = tuple()
            return _decorate(func, override_names)
        
        def _decorator(func):
            return _decorate(func, maybe_names)
        return _decorator

    return _decorator_entry
