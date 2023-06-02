import requests
from urllib import request
import lxml.etree as xmltree
from datetime import date, timedelta
from dateutil.relativedelta import *
from dateutil.rrule import rrule, MONTHLY, DAILY
import io
import PIL.Image as Image

import json

class Wms:
    def __init__(self) -> None:
        pass       

    def __converTimeDimensionToList(self, timeDimension: str):
        dateList = []
        if timeDimension is not None:
            intervals = timeDimension.split(',')
            for interval in intervals:
                intervalElements = interval.split('/')

                startDate_ = intervalElements[0].split('-')
                startYear = int(startDate_[0])
                startMonth = int(startDate_[1])
                startDay = int(startDate_[2])
                startDate = date(startYear, startMonth, startDay)

                endDate_ = intervalElements[1].split('-')
                endYear = int(endDate_[0])
                endMonth = int(endDate_[1])
                endDay = int(endDate_[2])
                endDate = date(endYear, endMonth, endDay)

                step = intervalElements[2]

                if step == 'P1D':
                    dateList += [dt.strftime("%Y-%m-%d") for dt in rrule(DAILY, dtstart=startDate, until=endDate)]
                elif step == 'P1M':
                    dateList += [dt.strftime("%Y-%m-%d") for dt in rrule(MONTHLY, dtstart=startDate, until=endDate)]

        return dateList

    def getCapabilities(self, outputFileName: str = 'output.tsv') -> None:
        wmsGetCapabilitiesUrl = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetCapabilities"
        response = requests.get(wmsGetCapabilitiesUrl)
        wmsTree = xmltree.fromstring(response.content)

        self.metaData = {}

        tsvHeader = "name\ttitle\tcrs\twestBound\teastBound\tnorthBound\tsouthBound\ttimeDimension\n"
        tsvData = tsvHeader

        for layer in wmsTree.findall("./{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer//*/"):
            try:
                if layer.tag == "{http://www.opengis.net/wms}Layer":
                    name = layer.find("{http://www.opengis.net/wms}Name").text
                    title = layer.find("{http://www.opengis.net/wms}Title").text
                    
                    crs = layer.find("{http://www.opengis.net/wms}CRS")
                    if crs is not None:
                        crsValue = crs.text
                    else:
                        crsValue = None
                    
                    bounds = layer.find("{http://www.opengis.net/wms}EX_GeographicBoundingBox")
                    if bounds is not None:
                        westBound = bounds.find("{http://www.opengis.net/wms}westBoundLongitude").text
                        eastBound = bounds.find("{http://www.opengis.net/wms}eastBoundLongitude").text
                        northBound = bounds.find("{http://www.opengis.net/wms}northBoundLatitude").text
                        southBound = bounds.find("{http://www.opengis.net/wms}southBoundLatitude").text
                    else:
                        westBound = None
                        eastBound = None
                        northBound = None
                        southBound = None

                    dimension = layer.find("{http://www.opengis.net/wms}Dimension")
                    if (dimension is not None) and (dimension.get("name") == 'time'):
                        timeDimension = dimension.text
                    else:
                        timeDimension = None

                    self.metaData[name] = {'title': title, 
                                  'crs': crsValue, 
                                  'bounds': {'westBound': westBound, 'eastBound': eastBound, 'northBound': northBound, 'southBound': southBound}, 
                                  'dateList': self.__converTimeDimensionToList(timeDimension)}

                    tsvData += f"{name}\t{title}\t{crsValue}\t{westBound}\t{eastBound}\t{northBound}\t{southBound}\t{timeDimension}\n"
            except Exception as e:
                print(f"An exception occured: {e}")
                
        with open('output.json', "w") as f:
            json.dump(self.metaData, f, indent=2)

        with open(outputFileName, "w") as f:
            f.write(tsvData)

    def __endpoint(self, layerName, crs, southBound, westBound, northBound, eastBound, runDate) -> str:
        baseUrl = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
        version = "1.3.0"
        format = "image/png"
        service = "WMS"
        requestType = "GetMap"
        height = 1000
        width = 1000

        if runDate is None:
            return f"{baseUrl}?version={version}&service={service}&request={requestType}&format={format}&STYLE=default&bbox={southBound},{westBound},{northBound},{eastBound}&CRS={crs}&HEIGHT={height}&WIDTH={width}&layers={layerName}"
        else:
            return f"{baseUrl}?version={version}&service={service}&request={requestType}&format={format}&STYLE=default&bbox={southBound},{westBound},{northBound},{eastBound}&CRS={crs}&HEIGHT={height}&WIDTH={width}&TIME={runDate}&layers={layerName}"

    def __imageDownloader(self, url, filePath):
        try:
            response = requests.get(url)
            img = Image.open(io.BytesIO(response.content))
            img.save(f"images/{filename}.png", "PNG")
        except Exception as e:
            print(e)

    def download(self):
        if self.metaData is None:
            raise Exception("No meta data is available. First run getCapabilities() method")
        else:
            for k, v in self.metaData.items():
                layerName = k
                crs = v['crs']
                southBound = v['bounds']['southBound']
                westBound = v['bounds']['westBound']
                northBound = v['bounds']['northBound']
                eastBound = v['bounds']['eastBound']
                dateList = v['dateList']

                if dateList == []:
                    url = self.__endpoint(layerName, crs, southBound, westBound, northBound, eastBound, None)
                    filePath = f"images/{layerName}.png"
                    self.__imageDownloader(url, filePath)
                else:
                    for runDate in dateList:
                        url = self.__endpoint(layerName, crs, southBound, westBound, northBound, eastBound, runDate)
                        filePath = f"images/{layerName}_{runDate}.png"
                        self.__imageDownloader(url, filePath)
    
