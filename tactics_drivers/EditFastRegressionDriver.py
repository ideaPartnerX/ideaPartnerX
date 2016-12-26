#!/usr/bin/env python
# -*- coding: utf-8 -*
# 用于数据数据编辑请求的挖掘驱动

__author__ = 'wangjun'

import traceback,re,json,sys,urllib
from Common.oracleUtil import OracleHelper
from Common.accessToken import AccessToken
from Common.logger import logger
from Common.settings import *
from Common.StructuralData import logDataManage
from Common.public import replaceIntForDict

reload(sys)
sys.setdefaultencoding('utf-8')
#请求数据挖掘
class  analyzeTacticsData:
    def __init__(self,conn,logger):
        self.conn=conn
        self.oracleObject=OracleHelper(conn,logger)
        self.user_id=None
        self.db_id=None
        self.log_id=None
        self._logger=logger
    #   按条件选取
    def getTempData(self):
        try:
            targetField = "ID,REQ,ACK,C_ID,\"DATE\",STATUS"
            sourceField = 'ID,REQ,ACK,FILEID,\"DATE\",STATUS'
            conditionString = "TO_CHAR(T.REQ) LIKE '%/service/edit/run/%' AND T.ID IN (SELECT F.ID FROM FIDDLER_BASE_DATA F MINUS SELECT S.ID FROM STRATEGY_EDIT_FAST_REGRESSION S) ORDER BY ID" #需补充条件
            sql = "INSERT INTO strategy_edit_fast_regression ({0}) SELECT {1} FROM fiddler_base_data T WHERE {2}".format(targetField, sourceField, conditionString)
            self._logger.Log(u"执行中间用例选取,执行SQL: %s" % sql, InfoLevel.INFO_Level)
            self.oracleObject.executeSQL(sql)
        except Exception as e:
            self._logger.Log(u"执行中间用例选取失败：%s" %traceback.format_exc(), InfoLevel.ERROR_Level)
    #   扩展字段赋值
    def setTempNewFieldData(self):
        try:
            upateSql="UPDATE STRATEGY_EDIT_FAST_REGRESSION SET DB_ID=:1,USER_ID=:2 WHERE ID=:3"
            sql="SELECT ID,to_char(REQ) as REQ FROM STRATEGY_EDIT_FAST_REGRESSION "
            tempData=self.oracleObject.executeSQL(sql)
            for temp in tempData:
                AccessToken=re.findall(r'.*access_token=(.*)&parameter',str(temp['REQ']))[0]
                tempReqParam=json.loads(re.findall(r'.*parameter=(.*)$',str(temp['REQ']))[0])
                temp['DB_ID']=tempReqParam['dbId']
                temp['USER_ID']=self.tokenObject().Token2UserID(AccessToken)
                self.oracleObject.changeData2WithParam(upateSql,[temp['DB_ID'],temp['USER_ID'],temp['ID']])
            self.oracleObject.commitData()
        except Exception as e:
            self._logger.Log(u"执行中间用例扩展字段赋值失败：%s" %traceback.format_exc(), InfoLevel.ERROR_Level)
    #   设置编辑类型
    def setTempTypeData(self):
        try:
            upateSql="UPDATE STRATEGY_EDIT_FAST_REGRESSION SET TYPE=:1,\"DESC\"=:2 WHERE ID=:3"
            sql="SELECT ID,to_char(REQ) as REQ FROM STRATEGY_EDIT_FAST_REGRESSION "
            tempData=self.oracleObject.executeSQL(sql)
            for temp in tempData:
                tempReqParam=json.loads(re.findall(r'.*parameter=(.*)$',str(temp['REQ']))[0])
                temp['type']=tempReqParam['type']
                temp['command']=tempReqParam['command']
                TypeCode=temp['command']+":"+temp['type']
                if TypeCode in InfoRoadEditType:
                    temp['TYPE']=TypeCode
                    temp['DESC']=InfoRoadEditType[TypeCode]
                else:
                    temp['TYPE']='Unkown type'
                    temp['DESC']='未知编辑操作0'
                self.oracleObject.changeData2WithParam(upateSql,[temp['TYPE'],temp['DESC'],temp['ID']])
            self.oracleObject.commitData()
        except Exception as e:
            self._logger.Log(u"执行中间用例扩展字段赋值失败：%s" %traceback.format_exc(), InfoLevel.ERROR_Level)
    #   计算分组
    def setTempGroupIdData(self):
        # sql="SELECT ID,REQ,TO_CHAR(ACK) FROM STRATEGY_EDIT_FAST_REGRESSION "
        # tempData=self.oracleObject.executeSQL(sql)
        # groupCount=1
        # TempArray=[]
        # for temp in tempData:
        #     temp['ACK']=json.loads(temp['TO_CHAR(ACK)'])
        #     TempArray.append(temp)
        # for Temp in TempArray:
        pass
    #   新增pid替换
    def replaceNewPidParam(self):
        #PidCode=-1
        pass
    def setTempLogidData(self):
        try:
            oracleObjectLog=OracleHelper(LogTestDBConf,self._logger)
            findLogSql="SELECT DISTINCT DATA_SET_ID FROM LOG_DETAIL WHERE REPLACE (OB_NM || OB_PID, '_', '') = '%s'"
            sql="SELECT ID,to_char(REQ) as REQ,TO_CHAR(ACK) FROM STRATEGY_EDIT_FAST_REGRESSION "
            updateLogIdSql="UPDATE STRATEGY_EDIT_FAST_REGRESSION SET LOG_ID=:1 WHERE ID=:2 AND (LOG_ID IS NULL OR LOG_ID IN ('Non find information', '数据集ID不唯一'))"
            tempData=self.oracleObject.executeSQL(sql)
            for temp in tempData:
                temp['REQ']=json.loads(re.findall(r'.*parameter=(.*)$',str(temp['REQ']))[0])
                temp['ACK']=eval(json.loads(temp['TO_CHAR(ACK)']))
                if 'type' not in temp['REQ'] or 'objId' not in temp['REQ']:
                   logid='error:Non find information'
                else:
                    tabNamePid=temp['REQ']['type']+str(temp['REQ']['objId'])
                    logList=oracleObjectLog.executeSQL(findLogSql%tabNamePid)
                    if not logList or len(logList) == 1:
                        logid=logList[0]['DATA_SET_ID']
                    elif len(logList)>1:
                        if temp['ACK']["data"]["log"]:
                            logArrag=[]
                            for log in temp['ACK']["data"]['log']:
                                if 'op' in log and log['op']!='新增':
                                    logArrag.append(log['type']+str(log['pid']))
                            AckFindLogidList=oracleObjectLog.executeSQL(self.getUnionLogSql(logArrag))
                            if not AckFindLogidList and len(AckFindLogidList)==1:
                                logid=AckFindLogidList[0]['DATA_SET_ID']
                            else:
                                logid='数据集ID不唯一'
                    else:
                        logid=None
                if logid:
                    self.oracleObject.changeData2WithParam(updateLogIdSql,[logid,temp['ID']])
            self.oracleObject.commitData()
        except Exception as e:
            self._logger.Log(u"执行中间用例登记LOGID赋值失败：%s" %traceback.format_exc(), InfoLevel.ERROR_Level)
    #   替换dbid userid
    def setTempDB_UseridAgain(self,dbid,userid,where):
        try:
            sql="UPDATE STRATEGY_EDIT_FAST_REGRESSION SET DB_ID=:1,USER_ID=:2 WHERE %s"%where
            self.oracleObject.changeData2WithParam(sql,[dbid,userid])
            self.oracleObject.commitData()
        except Exception as e:
            self._logger.Log(u"执行中间用例替换dbid/userid失败：%s" %traceback.format_exc(), InfoLevel.ERROR_Level)
    #计算联合语句
    def getUnionLogSql(self,list):
        baseSql="SELECT DISTINCT DATA_SET_ID FROM LOG_DETAIL WHERE REPLACE (OB_NM || OB_PID, '_', '') in ('%s')"
        valus="','".join(list)
        return baseSql%valus
    #创建票据对象
    def tokenObject(self):
        return AccessToken()

    def run(self):
        self.getTempData()
        self.setTempTypeData()
        self.setTempNewFieldData()
        self.setTempLogidData()

#驱动快速回归
class EditFastRegression:
    def __init__(self,conn,logger):
        self.OracleObject=OracleHelper(conn,logger)
        self.OracleObjectByLog=OracleHelper(LogTestDBConf,logger)
        self.OracleObjectRegion=None
        self.runList=[]
        # self.run=None
        self._logger=logger
    #初始化大区库
    #获取数据
    def getTestCaseData(self,c_id):
        try:
            FindSql="SELECT ID,TO_CHAR(REQ) AS REQ,TO_CHAR(ACK) AS ACK,DB_ID,USER_ID,LOG_ID,TYPE,\"DESC\" FROM STRATEGY_EDIT_FAST_REGRESSION WHERE C_ID='{0}'"
            self.runList=self.OracleObject.executeSQL(FindSql.format(c_id))
        except Exception as e:
            self._logger.Log(u"提取中间用例失败：%s" %traceback.format_exc(), InfoLevel.ERROR_Level)
    #获取大区库FM_Sys_Conf
    def getDbIdConn(self,dbid):
        ConnModel={"dbname":"orcl","host":None,"user":None,"passwd":None,"port":"1521"}
        FindSQL="SELECT A.DB_ID,A.DB_NAME,A.DB_USER_NAME,A.DB_USER_PASSWD,B.SERVER_IP,B.SERVER_PORT FROM DB_HUB A,DB_SERVER B WHERE A.DB_ID={0} AND A.SERVER_ID=B.SERVER_ID"
        oracleObject=OracleHelper(FM_Sys_Conf,self._logger)
        regionConnList=oracleObject.executeSQL(FindSQL.format(dbid))
        if regionConnList:
            # ConnModel['dbname']=regionConnList[0]['DB_NAME']
            ConnModel['host']=regionConnList[0]['SERVER_IP']
            ConnModel['user']=regionConnList[0]['DB_USER_NAME']
            ConnModel['passwd']=regionConnList[0]['DB_USER_PASSWD']
            ConnModel['port']=regionConnList[0]['SERVER_PORT']
            self.OracleObjectRegion=OracleHelper(ConnModel,self._logger)
        else:
            ConnModel=None
        return ConnModel
    #数据构建
    def bulidTestDataByLog(self,dbid,userid,logid):
        try:
            conn=self.getDbIdConn(dbid)
            if not conn:assert (conn)
            logDataManager=logDataManage(self.OracleObjectByLog,self.OracleObjectRegion,conn,'60561512',userid,logid,self._logger)
            logDataManager.structuralData()
        except Exception as e:
            self._logger.Log(u"提取goujian失败：%s" %traceback.format_exc(), InfoLevel.ERROR_Level)
    #公共函数替换数据
    def replaceData(self,string,findStr,replaceStr):
        return string.replace(findStr,replaceStr)
    #公共函数获取Token
    def getUser2Token(self,userid):
        userToken=AccessToken()
        return userToken.generate(userid,172800)

    #回滚测试和构建数据
    def rollbackDataByLog(self,dbid,userid,logid):
        try:
            conn=self.getDbIdConn(dbid)
            if not conn:assert (conn)
            #回滚大区库
            findGridsSql="SELECT DISTINCT grid_id FROM LOG_DETAIL_GRID "
            Grids=self.OracleObjectRegion.executeSQL(findGridsSql)
            for grid in Grids:
                logDataManagerByRegion=logDataManage(self.OracleObjectByLog,self.OracleObjectRegion,conn,grid['GRID_ID'],userid,logid,self._logger)
                logDataManagerByRegion.rollbackRegionData()
                logDataManagerByRegion.cleanLog()
            #回滚构建数据
            logDataManager=logDataManage(self.OracleObjectByLog,self.OracleObjectRegion,conn,'60561512',userid,logid,self._logger)
            logDataManager.rollbackData()
        except Exception as e:
            self._logger.Log(u"回滚数据失败：%s" %traceback.format_exc(), InfoLevel.ERROR_Level)
    #执行测试请求验证返回值
    def replayHttp(self,req,ack,type,id):
        from Common.jsonDiff import verifyData
        updateSql="UPDATE STRATEGY_EDIT_FAST_REGRESSION SET RESULT=:1 WHERE ID=:2"
        try:
            httpObject=urllib.urlopen(req)
            self._logger.Log(u"执行%s操作请求成功,URL:%s"%(type,req), InfoLevel.INFO_Level)
            responeValue=httpObject.read()
            self._logger.Log(u"执行%s操作请求返回值,URL:%s"%(type,responeValue), InfoLevel.INFO_Level)
            respone=json.loads(responeValue)
            if type.startswith('CREATE:'):
                respone=replaceIntForDict(respone)
                ack=replaceIntForDict(ack)
                result=verifyData(ack,respone)
            else:
                result=verifyData(ack,respone)
            if len(result)==0:
                code='Pass'
            else:
                code='Failed'
            self.OracleObject.changeData2WithParam(updateSql,[code,id])
            self.OracleObject.commitData()
        except Exception as e:
            self._logger.Log(u"执行http请求失败：%s" %traceback.format_exc(), InfoLevel.ERROR_Level)

    def run(self):
        pass

if __name__ == '__main__':
    Logger=logger(logfilename)
    Conn={"dbname":"orcl","host":"192.168.4.61","user":"fm_regiondb260_test_d_208","passwd":"fm_regiondb260_test_d_208","port":"1521"}
    sourceField='NUMID,EXEC_URL,RESPONSE,RESP_TIME'
    conditionString="TO_CHAR(EXEC_URL) LIKE '%/service/edit/run/%' ORDER BY NUMID"
    #sql="INSERT INTO  strategy_edit_fast_regression ({0}) SELECT {1} FROM EDIT_BASE_DATA_ZQ  WHERE {2}".format(targetField,sourceField,conditionString)
    sql="SELECT {0} FROM EDIT_BASE_DATA_ZQ  WHERE {1}".format(sourceField,conditionString)
    print sql
    object1=OracleHelper(Conn,Logger)
    TacticsData=object1.executeSQL(sql)
    print TacticsData
    for Data in TacticsData:
        print Data['EXEC_URL']


    #ATD=analyzeTacticsData(Conn,Logger)
    #ATD.getTempData()