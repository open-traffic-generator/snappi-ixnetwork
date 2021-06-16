from snappi_ixnetwork.ixnetworkapi import Api
# import inspect
# from snappi_ixnetwork.exceptions import SnappiIxnException
#
# supported_modules = ['snappi.snappi',
#                      'snappi_convergence.snappi_convergence']
# module_name = None
# for frame in inspect.stack():
#     module = inspect.getmodule(frame.frame)
#     if module is not None:
#         name = module.__name__
#         if name in supported_modules:
#             module_name = name
#             break
#
# if module_name == 'snappi.snappi':
#     from snappi_ixnetwork.ixnetworkapi import Api
# elif module_name == 'snappi_convergence.snappi_convergence':
#     from snappi_ixnetwork.convergenceapi import Api
# else:
#     raise SnappiIxnException(500, "Module is not supported")