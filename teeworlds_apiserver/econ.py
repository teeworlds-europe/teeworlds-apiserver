import functools
from asyncio import (
    open_connection,
    Lock,
)


def acquire(*modes):
    def outer(f):
        @functools.wraps(f)
        async def inner(self, *args, **kwargs):
            for mode in modes:
                await getattr(self, f'{mode}_lock').acquire()
            try:
                return await f(self, *args, **kwargs)
            finally:
                for mode in modes:
                    getattr(self, f'{mode}_lock').release()
        return inner
    return outer


class TeeworldsECON:

    ALLOWED_COMMANDS = (
        'echo',
        'exec',
        'kick',
        'ban',
        'unban',
        'bans',
        'status',
        'shutdown',
        'reload',
        'record',
        'stoprecord',
        'tune',
        'tune_reset',
        'tune_dump',
        'change_map',
        'restart',
        'broadcast',
        'say',
        'set_team',
        'set_team_all',
        'add_vote',
        'remove_vote',
        'force_vote',
        'clear_votes',
        'vote',
    )

    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.reader = None
        self.writer = None
        self.read_lock = Lock()
        self.write_lock = Lock()

    @acquire('write', 'read')
    async def connect(self):
        if self.writer is not None:
            self.writer.close()
            await self.writer.wait_closed()
        try:
            self.reader, self.writer = await open_connection(
                self.host, self.port,
            )
            print(f'Connected to {self.host}:{self.port}')
            self.writer.write(f'{self.password}\n'.encode())
            await self.writer.drain()
            # Skip password prompt
            await self.reader.readline()
            line = await self.reader.readline()
            if 'Authentication successful' \
                    not in line.decode('utf-8'):
                raise ConnectionError(
                    f'Failed to authenticate to {self.host}:{self.port}'
                )
        except ConnectionError as e:
            print(f'Failed to connect to {self.host}:{self.port}')
            raise e

    async def disconnect(self):
        if self.writer is not None:
            self.writer.close()
            return await self.writer.wait_closed()

    def is_closing(self):
        if self.writer is None:
            return True
        else:
            return self.writer.is_closing()

    @staticmethod
    def validate_string(r):
        # Prevent flooding
        r = r[:120]
        # Prevent command injection
        r.replace('\n', ' ')
        return r

    @acquire('write')
    async def command(self, command, *args):
        if command not in self.ALLOWED_COMMANDS:
            raise ValueError(f'Invalid command: {command}')
        message = command + ' ' + self.validate_string(' '.join(args)) + '\n'
        self.writer.write(message.encode())
        await self.writer.drain()

    @acquire('read')
    async def readline(self):
        r = (await self.reader.readline()).decode('utf-8')
        if r == '':
            self.writer.close()
            raise ConnectionError(
                f'Connection to {self.host}:{self.port} has been closed'
            )
        else:
            return r.replace('\0', '').rstrip()
