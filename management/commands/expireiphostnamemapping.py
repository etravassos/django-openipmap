#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from openipmap.models import IPMeta
from openipmap.utils import do_dns_host_lookup,do_dns_loc_lookup
from datetime import datetime
import pytz

UPDATE_INTERVAL=86400 # one day

def total_seconds( td ):
   return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

def check_and_expire( ip, ipm_list, now ):
   ''' given an IP address and a list of IPMeta objects for that IP, expire all info in db that is not up to date '''
   print "%s %s" %  (ip, len( ipm_list ) )
   if len( ipm_list ) > 1:
      ### pick one, rest should have been invalidated anyways
      for ipm in ipm_list[1:]:
         ipm.invalidated=now
         ipm.save()
   ipm = ipm_list[0] # this is the chosen ipmeta object to validate against
   now_dnshost = None
   now_dnsloc = None
   now_dnshost = do_dns_host_lookup( ip )
   if now_dnshost != None:
      now_dnsloc = do_dns_loc_lookup( now_dnshost )
   if ipm.hostname != now_dnshost or ipm.dnsloc != now_dnsloc:
      # invalidate old and create new
      ipm.invalidated = now
      ipm.save()
      # clone didn't work ( https://docs.djangoproject.com/en/1.7/topics/db/queries/#copying-model-instances )
      # so doing a new object for now
      print "creating new! for %s/%s" % ( ipm.ip , ipm.hostname )
      ipm_new = IPMeta(
         ip= ipm.ip
      )
      ipm_new.save() ## this will do another DNS lookup (which should be in cache anyways)

class Command(BaseCommand):
   args = ''
   help = 'Expires IP->Hostname mappings from the ipmeta table'
   def handle(self, *args, **options):
         now = datetime.now(pytz.utc)
         ips = set()
         current_ip = None
         ipm_list = []
         for ipm in IPMeta.objects.filter(invalidated=None).order_by('ip'):
            if current_ip == None:
               current_ip = ipm.ip
            if current_ip == ipm.ip: ## add it to ipm_list
               ipm_list.append( ipm )
               continue
            else:
               ## check validity for this IP and update if needed
               check_and_expire( current_ip , ipm_list, now )
               # reset
               ipm_list = [ipm]
               current_ip = ipm.ip
         check_and_expire( current_ip, ipm_list, now )      
         
'''
            if ipm.invalidated == None and ipm.hostname == None or total_seconds(now - ipm.last_updated) > UPDATE_INTERVAL: ###TODO check last-updated against current time:
                  now_dnshost = None
                  now_dnsloc = None
                  now_dnshost = do_dns_host_lookup( ipm.ip )
                  try:
                     now_dnshost = now_dnshost.rstrip('.')
                  except: pass ## will fail if dnshost=none
                  if now_dnshost != None:
                     now_dnsloc = do_dns_loc_lookup( now_dnshost )
                  if ipm.hostname != now_dnshost or ipm.dnsloc != now_dnsloc:
                     # invalidate old and create new
                     ipm.invalidated = now
                     ipm.save()
                     # clone didn't work ( https://docs.djangoproject.com/en/1.7/topics/db/queries/#copying-model-instances )
                     # so doing a new object for now
                     print "creating new! for %s/%s" % ( ipm.ip , ipm.hostname )
                     ipm_new = IPMeta(
                        ip= ipm.ip
                     )
                     ipm_new.save() ## this will do another DNS lookup (which should be in cache anyways)
                     # this didnt work:
                     #ipm.invalidated = None
                     #ipm.hostname = now_dnshost
                     #ipm.dnsloc   = now_dnsloc
                     #ipm.save()
            #TODO: case of retry/expiry due to being too old
            # retry/expire after a week?
'''
