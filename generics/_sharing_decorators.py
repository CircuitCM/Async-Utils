from functools import wraps
import asyncio as aio


def _wrapfunc(func,*args,**kwargs):

    return args,kwargs
#either client is the last required arg or its one of the kwargs
#@decorator
def rclient_wrapper(func):
    if aio.iscoroutinefunction(func):
        @wraps(func)
        async def _r(*args,**kwargs):
            #cn=kwargs.get('rclient',0)
            if len(args)>0:
                pcn = args[-1]
                if type(pcn)==DataAsync:
                    cn=pcn
                else:
                    cn = kwargs.get('rclient', 0)
            else:
                cn = kwargs.get('rclient', 0)
            #connection is arg in cn
            # if cn == 0:
            #     return await func(*(*args, rClient()), **kwargs)
            # connection is kwarg and required
            if cn == 0 or cn is None:
                if 'rclient' in kwargs:del kwargs['rclient']
                return await func(*args,**{'rclient':rClient(),**kwargs})
            else:
                return await func(*args, **kwargs)
            # if cn ==0 or cn is None:
            #     return await func(*args,**({'rclient':rClient()}|kwargs))
            # #connection is kwarg and required
            # else:
            #     return await func(*args,**kwargs)
    else:
        @wraps(func)
        def _r(*args, **kwargs):
            # cn=kwargs.get('rclient',0)
            if len(args) > 0:
                pcn = args[-1]
                if type(pcn) == DataAsync:
                    cn = pcn
                else:
                    cn = kwargs.get('rclient', 0)
            else:
                cn = kwargs.get('rclient', 0)
            # connection is arg in cn
            # if cn == 0:
            #     return func(*(*args, rClient()), **kwargs)
            # connection is kwarg or required
            if cn == 0 or cn is None:
                if 'rclient' in kwargs: del kwargs['rclient']
                return func(*args,**{'rclient':rClient(),**kwargs})
            else:
                return func(*args, **kwargs)
            # if cn == 0 or cn is None:
            #     return func(*args, **({'rclient': rClient()} | kwargs))
            # # connection is kwarg and required
            # else:
            #     return func(*args, **kwargs)
    return _r


def ryield_wrapper(func):
    if aio.iscoroutinefunction(func):
        @wraps(func)
        async def _r(*args,**kwargs):
            if len(args)>0:
                pcn = args[-1]
                if type(pcn)==DataAsync:
                    cn=pcn
                else:
                    #probably shouldn't use zero for this, something more obscure like a class I made here
                    cn = kwargs.get('rclient', 0)
            else:
                cn = kwargs.get('rclient', 0)
            #0 means assume its a arg (cause no kwarg) but no variable given, so just stick it in there. It will also be last arg if not a kwarg.
            # if cn ==0:
            #     fnc= func(*(*args,rClient()),**kwargs)
            #connection is kwarg and required
            if cn ==0 or cn is None:
                if 'rclient' in kwargs: del kwargs['rclient']
                fnc=func(*args,**{'rclient':rClient(),**kwargs})
            else:
                fnc=func(*args,**kwargs)
            async for i in fnc:
                yield i
    else:
        @wraps(func)
        def _r(*args, **kwargs):
            if len(args) > 0:
                pcn = args[-1]
                if type(pcn) == DataAsync:
                    cn = pcn
                else:
                    # probably shouldn't use zero for this, something more obscure like a class I made here
                    cn = kwargs.get('rclient', 0)
            else:
                cn = kwargs.get('rclient', 0)
            # 0 means assume its a arg (cause no kwarg) but no variable given, so just stick it in there. It will also be last arg if not a kwarg.
            # if cn == 0:
            #     fnc = func(*(*args, rClient()), **kwargs)
            # connection is kwarg and required
            if cn ==0 or cn is None:
                if 'rclient' in kwargs: del kwargs['rclient']
                fnc = func(*args, **{'rclient': rClient(), **kwargs})
            else:
                fnc = func(*args, **kwargs)
            for i in fnc:
                yield i

    return _r
