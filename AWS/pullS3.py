"""
Author: David Jorge

This library acts as an API between the dashboard app and AWS. It allows for data to be pulled
from AWS, and parsed/saved accordingly into more convenient formats.
"""

import binascii
import boto3
import pandas as pd
from PIL import Image, ImageFile
from io import BytesIO
import datetime


def datetimeToString(dt):
    """
    Converts datetime object into string for file naming.

    :param dt: datetime object.
    :return: string.
    """
    return str(dt)[:10] + "-" + str(dt)[11:13] + "-" + str(dt)[14:16] + "-" + str(dt)[17:19]


def roundTime(dt=None, roundTo=60):
    """Round a datetime object to any time lapse in seconds
    dt : datetime.datetime object, default now.
    roundTo : Closest number of seconds to round to, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
    """
    if dt == None: dt = datetime.datetime.now()
    seconds = (dt.replace(tzinfo=None) - dt.min).seconds
    rounding = (seconds + roundTo / 2) // roundTo * roundTo
    return dt + datetime.timedelta(0, rounding - seconds, -dt.microsecond)


def getIndexes(dfObj, value):
    """ Get index positions of value in dataframe i.e. dfObj."""
    listOfPos = list()
    # Get bool dataframe with True at positions where the given value exists
    result = dfObj.isin([value])
    # Get list of columns that contains the value
    seriesObj = result.any()
    columnNames = list(seriesObj[seriesObj == True].index)
    # Iterate over list of columns and fetch the rows indexes where value exists
    for col in columnNames:
        rows = list(result[col][result[col] == True].index)
        for row in rows:
            listOfPos.append((row, col))
    # Return a list of tuples indicating the positions of value in the dataframe
    return listOfPos


class pullS3:
    """
    Class for managing and processing data pulls from aws
    """

    def __init__(self):
        """
        files: List of filenames processed during instance lifetime
        mostRecent: String - Most recently added filename from aws.
        map_data: Pandas dataframe - stores number of object detections, date, latitude and longitude.
        hourly: Pandas dataframe - stores date and count information in hourly intervals.
        """
        self.s3 = boto3.resource(
            service_name='s3',
            region_name='eu-west-2',
            aws_access_key_id='#',
            aws_secret_access_key='#'
        )
        self.files = []
        self.mostRecent = None
        self.map_data = pd.DataFrame(
            columns=['Number of Clusters', 'Date', "lat", "lon", "temp", "humidity", "pressure", "pitch", "roll",
                     "yaw", "_size_"])
        self.hourly = pd.DataFrame(columns=["Date", "Count"])

    def flushBucket(self, bucketname='oceanpollution'):
        """
        Flushes target bucket in AWS. Use with caution.

        :param bucketname: S3 bucket name
        """
        for obj in self.s3.Bucket(bucketname).objects.all():
            obj.delete()

    def pull(self):
        """
        Pulls data from S3 bucket in AWS and processes it.

        :return: Most Recent file name, Parcel Condition Label
        """
        # Print available bucket names
        for bucket in self.s3.buckets.all():
            # print(bucket.name)
            pass

        # Get bucket size
        size = 0
        for obj in self.s3.Bucket('oceanpollution').objects.all():
            size += 1
            # print(obj.get()['Body'].read())

        images = []  # List of images as byte arrays
        parsing = False  # Flags whether or not an image the current AWS bucket entry is part of an image
        metadata = None  # Entry metadata
        """
        Each detection by the camera is sent to AWS in the following format:
        {Image Start,__headers__}   # marks the start of an entry, __headers__ is comma separated
        image hex string            # There can be multiple image hex strings
        {Image End}                 # marks the end of an entry
        """
        for obj in self.s3.Bucket('oceanpollution').objects.all():
            if "Image Start" in obj.get()['Body'].read().decode():
                parsing = True
                arr = bytearray()
                metadata = obj.get()['Body'].read().decode().replace('}', "").replace('[', "").replace(']', "").split(
                    ',')[1:]
                if len(metadata) < 10:
                    parsing = False
                continue
            if parsing and obj.get()['Body'].read().decode() != "{Image Start}":
                if obj.get()['Body'].read().decode() == "{Image End}":
                    images.append((arr, obj.get()['LastModified'], metadata))
                    metadata = None
                    parsing = False
                    continue
                arr.extend(binascii.unhexlify(obj.get()['Body'].read()))
        # print(images)

        # Get most recent entry
        newest = None
        if images:
            newest = images[0]

        # Save parsed images as files. Same entries are not processed more than once per instance
        # map_data and hourly instance variables are updated accordingly
        for img in images:
            if not datetimeToString(img[1]) in self.files:
                im = Image.open(BytesIO(img[0]))
                # im.show()
                im.save("./assets/{}.png".format(datetimeToString(img[1])))
                if img[2]:
                    self.map_data = self.map_data.append(
                        {"Number of Clusters": float(img[2][2]), "Date": datetimeToString(img[1]),
                         "lat": float(img[2][0]), "lon": float(img[2][1]), "temp": float(img[2][4]),
                         "humidity": float(img[2][5]), "pressure": float(img[2][6]), "pitch": float(img[2][7]),
                         "roll": float(img[2][8]), "yaw": float(img[2][9]), "_size_": float(img[2][2])+1},
                        ignore_index=True)
                self.files.append(datetimeToString(img[1]))
                roundDate = roundTime(img[1], 60 * 60)
                if roundDate not in self.hourly.values:
                    self.hourly = self.hourly.append({"Date": roundDate, "Count": 0}, ignore_index=True)
                loc = getIndexes(self.hourly, roundDate)[0][0]
                self.hourly.at[loc, "Count"] += 1

            newest = img
        print("Pulled Data from AWS!")
        self.mostRecent = datetimeToString(newest[1])


if __name__ == "__main__":
    aws = pullS3()
    aws.pull()
    print(aws.map_data['lat'].to_numpy())
    # print(aws.hourly)
