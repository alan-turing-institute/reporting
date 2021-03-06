#-- -----------------------------------------------------------------------------------------
#-- Job Name        : Registration DB Streaming
#-- DB Name 	    : RegPrc DB
#-- Purpose    	    : Job connects to kafka topic and stream data in real time and process the data, then index data on to elastic search index
#--           
#-- Create By       : Sadanandegowda DM
#-- Created Date    : Sep-2020
#-- 
#-- Modified Date        Modified By         Comments / Remarks
#-- ------------------------------------------------------------------------------------------
#-- 
#-- ------------------------------------------------------------------------------------------

#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from datetime import datetime
from elasticsearch import Elasticsearch

import configparser
import pprint, StringIO
import json
import datetime

if __name__ == "__main__":
     sc = SparkContext(appName="KafkaStreamFromDB")
     ssc = StreamingContext(sc, 2)
     brokers, topic = sys.argv[1:]
     kStream = KafkaUtils.createDirectStream(ssc, [topic],{"metadata.broker.list": brokers})
     dbRecord = kStream.map(lambda x: x[1])
       
     dbRecord.pprint()

     config = configparser.ConfigParser()
     config.read('appconfig.properties')

     eshost = config.get("ElasticSearchSection", "eshost")
     esuser = config.get("ElasticSearchSection", "esuser")
     espassword = config.get("ElasticSearchSection", "espassword")
     esport = int(config.get("ElasticSearchSection", "esport"))
     indexname = config.get("ElasticSearchSection", "regclient-indexname")     

     es = Elasticsearch(eshost, http_auth=(esuser, espassword), port=esport)
     p=es.ping()
     print(p)
   
     def sendRecord(rdd):
        
 	 #collect the RDD to a list
  	 list_elements = rdd.collect()
         
  	 #process record list
  	 for element in list_elements:
             #convert string to python dictionary
             record = json.loads(element)
             
             #Extract the id for unique key for elasticsearch index
             docId = record['id']
             print(docId)

             record['center_id'] = record['reg_id'][0:5]
             record['date'] = convertEpochDate(record['cr_dtimes'])
	     
             reg_cr_dtimes = convertEpochDateTime(record['cr_dtimes'])
             reg_upd_dtimes = convertEpochDateTime(record['upd_dtimes'])
             reg_del_dtimes = convertEpochDateTime(record['del_dtimes'])

             record['cr_dtimes'] = reg_cr_dtimes
             record['upd_dtimes'] = reg_upd_dtimes
             record['del_dtimes'] = reg_del_dtimes
             print(record)
        
             res = es.index(index=indexname, id=docId, body=record)
             print(res['result'])
             es.indices.refresh(index=indexname)

     dbRecord.foreachRDD(sendRecord)

     def convertEpochDateTime(epochDateTime):
         if epochDateTime is not None:
            dtimes_str = str(epochDateTime)
            dtimes_upd = dtimes_str[0:-6]
            sDateTime = datetime.datetime.fromtimestamp(int(dtimes_upd)).strftime('%Y-%m-%dT%H:%M:%S.000Z')                                                   
            return sDateTime
         else:
            return None

     def convertEpochDate(epochDate):
         if epochDate is not None:
            dtimes_str = str(epochDate)
            dtimes_upd = dtimes_str[0:-6]
            sDate = datetime.datetime.fromtimestamp(int(dtimes_upd)).strftime('%Y-%m-%d')
            return sDate
         else:
            return None
    
     ssc.start()
     ssc.awaitTermination()
