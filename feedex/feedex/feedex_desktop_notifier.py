# -*- coding: utf-8 -*-
""" Desktop notifier classes for FEEDEX """



import gi
gi.require_version('Notify', '0.7')

from gi.repository import Notify

    
from feedex_headers import *







class DesktopNotifier:
    """ Desktop notification handler for FEEDEX. Displays notifications given a result list """
    def __init__(self, **kargs):
        Notify.init("Feedex")
        self.entry = ResultEntry()
        self.notif_list = []
        self.parent = kargs.get('parent')
        self.icons = kargs.get('icons', fdx.icons_cache)

    def show(self):
        """ Show all queued notifications """
        for n in self.notif_list:
            time.sleep(0.1)
            n.show()

    def clear(self): self.notif_list.clear()
        

    def load(self, results:list, **kargs):
        """ Load result lists to use """

        for r in results:
            
            self.entry.clear()
            self.entry.populate(r)

            if self.entry['id'] is None: continue

            if scast(self.entry['flag'], int, 0) > 0: title = f"!{self.entry['flag_name']}: {self.entry['feed_name']}"
            else: title = f"{self.entry['feed_name']}"
    
            n = Notify.Notification.new(title, f"{self.entry['title']}", icon=self.icons.get(self.entry['feed_id']))
            n.set_timeout(0)

            if scast(self.entry['flag'], int, 0) > 0: n.set_urgency(2)
            else: n.set_urgency(1)

            self.notif_list.append(n)


    def notify(self, icon, title:str, body:str):
        """ Quickly send a desktop notification """
        if icon is not None: 
            if type(icon) is str: icon = os.path.join(FEEDEX_SYS_ICON_PATH, f'{icon.lower()}.svg')
            else: icon = self.icons.get(icon)

        n = Notify.Notification.new(title, body, icon)
        n.set_timeout(0)
        n.show()



