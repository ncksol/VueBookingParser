import os
import re
import logging
import sys
import traceback
from datetime import datetime
from time import sleep
from bs4_parser import BS4Parser
from azure_storage_logging.handlers import TableStorageHandler

#
# The azure library provides access to services made available by the
# Microsoft Azure platform, such as storage and messaging.
#
# See http://go.microsoft.com/fwlink/?linkid=254360 for documentation and
# example code.
#
from azure.servicebus import ServiceBusService
from azure.storage import CloudStorageAccount
from azure.servicebus import Message

#
#
# Service Bus is a messaging solution for applications.  It sits between
# components of your applications and enables them to exchange messages in a
# loosely coupled way for improved scale and resiliency.
#
# See http://go.microsoft.com/fwlink/?linkid=246934 for Service Bus
# documentation.
#
SERVICE_BUS_NAMESPACE = 'VueBooking'
SERVICE_BUS_KEY = '8vN1AglsV2hR0KGGuB0BnF/4hMzVraCkMIzHnm+opQU='
SERVICE_BUS_KEYNAME = 'RootManageSharedAccessKey'
bus_service = ServiceBusService(service_namespace=SERVICE_BUS_NAMESPACE,
    shared_access_key_name=SERVICE_BUS_KEYNAME,
    shared_access_key_value=SERVICE_BUS_KEY)

logger = logging.getLogger("myLogger")
handler = TableStorageHandler(account_name="vuebookingparser", account_key="YGO8j2C8CK3W50/Sfxa5t+8VtEerJzDKEZxnNDui9E6YD8PxgH1UUuZvyp0KZzNidiuDs5sRxE9ObxIDXG3Ypg==", table="MyLogs")
logger.addHandler(handler)


def Process():                
    bookingEmailMessage = bus_service.receive_queue_message('bookingemailsin', peek_lock = True)
    data = bookingEmailMessage.body
                    
    if data == None or data == "":
        return

    if __debug__:
        logger.warning("email body loaded")
        
    ParseEmail(data)
    
    bookingEmailMessage.delete()

    if __debug__:
        logger.warning("message removed")

def ParseEmail(data):
    with BS4Parser(data, "html5lib") as html:
        dateTimeCell = html.find(string=re.compile("\d:\d\d\s(PM|AM)"))
        if dateTimeCell == None:
            logger.error("Unable to find date and time in the body:\n%s", data)
            return

        if __debug__:
            logger.warning("datetime cell found")

        filmCell = html.find('td', attrs={"style":"text-decoration:none; text-align:left; font-size:22px; font-family:arial,helvetica,sans-serif; font-weight:normal; color:rgb(247,148,30); text-transform:uppercase; border-collapse:collapse; border-spacing:0px; padding:0px"})
        if filmCell == None:
            logger.warning("Unable to find film name: %s", data)
        else:
            filmName = filmCell.text.strip()

        dateTimeString = str(datetime.now().year) + " " + str(dateTimeCell).strip()

        if __debug__:
            logger.warning("datetime: {a}".format(a = dateTimeString))

        dateObject = datetime.strptime(dateTimeString, "%Y %a %d %b, %I:%M %p")
        formattedDateTime = dateObject.strftime("%Y-%m-%d %H:%M:%S")          

        ticketImgCell = html.find(src=re.compile("vu/tickets.png"))
        reference = ticketImgCell.parent.parent.parent.parent.parent.parent.contents[5].contents[1].contents[1].contents[1].contents[3].text.strip()

        label = filmName + ' ' + reference
        properties = '{"Label": "%s"}' % label

        if __debug__:
            logger.warning("label: {a}".format(a = label))

        dateTimeMessage = Message(bytes(formattedDateTime, "utf-8"), bus_service, broker_properties=properties)            
        success = bus_service.send_queue_message("bookingeventout", dateTimeMessage)

        if __debug__:
            logger.warning("message sent")


if __name__ == '__main__':
    while True:
        try:
            Process()        
        except Exception as e:
            logger.error(traceback.format_exc())
        
        if __debug__:
            sleep(10)
        else:
            sleep(600)

            