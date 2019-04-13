from google.appengine.ext import vendor
vendor.add("lib")

# import os
# import google
# import imp
# import inspect
# from google.appengine.ext import vendor

# from google.appengine.tools.devappserver2.python import sandbox
# sandbox._WHITE_LIST_C_MODULES += ['_ssl', '_socket']

# runtime_path = os.path.realpath(inspect.getsourcefile(inspect))
# runtime_dir = os.path.dirname(runtime_path)

# # Patch and reload the socket module implementation.
# system_socket = os.path.join(runtime_dir, 'socket.py')
# imp.load_source('socket', system_socket)

# # Patch and reload the ssl module implementation.
# system_ssl = os.path.join(runtime_dir, 'ssl.py')
# imp.load_source('ssl', system_ssl)

# vendor.add("lib")