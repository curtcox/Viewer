# Gunicorn configuration file
bind = "0.0.0.0:5000"
reload = True
reuse_port = True

# Set log level to WARNING to suppress INFO level WINCH signal messages
loglevel = "warning"

# Custom log format without excessive signal handling messages
def on_starting(server):
    server.log.info("Starting Gunicorn server")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    pass

def post_fork(server, worker):
    pass

def post_worker_init(worker):
    pass

def worker_abort(worker):
    pass

def pre_exec(server):
    server.log.info("Forked child, re-executing.")