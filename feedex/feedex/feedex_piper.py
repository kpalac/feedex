# -*- coding: utf-8 -*-
""" 
Handler class for IPC and pipes

"""

from feedex_headers import *

import struct
import select


class FeedexReqError(FeedexError):
    def __init__(self, *args, **kargs):
        kargs['code'] = FX_ERROR_REQ
        super().__init__(*args, **kargs)
        


class FeedexRequest:
    """ Basic request template """
    
    def __init__(self, **kargs) -> None:
    
        self.ent, self.act, self.body = kargs.get('ent'), kargs.get('act'), kargs.get('body')
        self.session_id = kargs.get('session_id', fdx.session_id)

        self.size = 0
        self.protocol = None

        self.error = 0

        self.ts = None

        self.content = None
        self.req_str = None




    def validate(self, **kargs):
        """ Validate request """
        self.ent, self.act, self.body = scast(self.ent, int, -1), scast(self.act, int, -1), scast(self.body, dict, None)
        if self.ent not in FX_ENTITIES: 
            self.error = FX_ERROR_REQ
            return self.error, _('Invalid enity given!')

        if self.act not in FX_ACTIONS:
            self.error = FX_ERROR_REQ
            return self.error, _('Invalid action given!')

        if self.body is None:
            self.error = FX_ERROR_REQ
            return self.error, _('Body must be a dict!')
        
        return 0


    def _buid_content(self, **kargs):
        """ Builds request content from components """
        self.content = {'session_id':self.session_id, 'protocol':self.protocol, 'timestamp':self.ts, 'entity':self.ent, 'action':self.act, 'body':self.body}


    def encode(self, **kargs):
        """ Send request to a pipe """
        self.protocol = kargs.get('protocol', 'local')

        now = datetime.now()
        self.ts = int(now.timestamp())

        err = self.validate()
        if err != 0: raise FeedexReqError(*err)

        self._buid_content()

        try: self.req_str = json.dumps(self.content)
        except (IOError, json.JSONDecodeError,) as e: 
            self.error = FX_ERROR_IO
            raise FeedexReqError(_('Could not convert request to JSON: %a'), e)
        
        self.size = len(self.req_str)
        return 0




    def decode(self, req_string, **kargs):
        """ Decode request from stream """
        self.req_str = scast(req_string, str, '')
        self.size = len(self.req_str)

        try: self.content = json.loads(self.req_str)
        except (IOError, json.JSONDecodeError,) as e:
            self.error = FX_ERROR_IO
            raise FeedexReqError(_('Error decoding request string: %a'), e)

        self.content = scast(self.content, dict, None)
        if type(self.content) is not dict:
            self.error = FX_ERROR_REQ
            raise FeedexReqError(_('Input must be a dict!'))

        self.session_id = self.content.get('session_id')
        self.ts = self.content.get('timestamp')
        self.protocol = self.content.get('protocol')

        self.ent = self.content.get('entity')
        self.act = self.content.get('action')
        self.body = self.content.get('body')

        err = self.validate()
        if err != 0: raise FeedexReqError(*err)
        return 0









class FeedexPiper:
    """ Class for listeners on pipes etc."""
    def __init__(self, **kargs) -> None: pass
        

    def send_local(self, pipe,  ent, act, body, **kargs):
        """ Send request to local pipe """

        req = FeedexRequest(ent=ent, act=act, body=body, session_id=kargs.get('session_id'))
        try: req.encode()
        except FeedexReqError as e: return FX_ERROR_REQ

        # Add size header
        req_str = struct.pack("<I", req.size) + req.req_str.encode("utf8")

        # Write to fifo
        try:
            fifo = os.open(pipe, os.O_WRONLY)
            os.write(fifo, req_str)
            debug(6, f'Request sent: {req.content}')
        except (OSError, IOError,) as e: return msg(FX_ERROR_REQ, _('Error writing to %a pipe: %b'), pipe, e)
        finally: os.close(fifo)
        return 0





    def local_pipe_listen(self):
        """ Listens on local input pipe and processes requests """
        try: fifo = os.open(fdx.in_pipe, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as e: return msg(FX_ERROR_IO, _('Could not open %a pipe: %b'), fdx.in_pipe, e)

        try:
            poll = select.poll()
            poll.register(fifo, select.POLLIN)
        except select.error as e: return msg(FX_ERROR_IO, _('Could not register %a pipe: %b'), fdx.in_pipe, e)

        debug(6, f'Started listening on pipe {fdx.in_pipe}')
        while fdx.listen:
             if (fifo, select.POLLIN) in poll.poll(2000):
                req_size_raw = os.read(fifo, 4)
                req_size = struct.unpack("<I", req_size_raw)[0]
                req_str = os.read(fifo, req_size).decode("utf8")
                debug(6, f'Request received: {req_str}')
                req = FeedexRequest()

                try: err = req.decode(req_str)
                except FeedexReqError: continue

                if err != 0: continue

                if req.session_id != fdx.session_id:
                    msg(FX_ERROR_REQ, _('Request session id mismatch!'))
                    continue

                if req.protocol != 'local':
                    msg(FX_ERROR_REQ, _('Request protocol mismatch!'))
                    continue

                fdx.req_append(req)
                fdx.bus_append(FX_ACTION_HANDLE_REQUEST)
                debug(6, 'Request sent to bus')

        poll.unregister(fifo)
        os.close(fifo)