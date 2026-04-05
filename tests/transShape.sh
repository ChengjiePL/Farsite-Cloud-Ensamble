#!/bin/bash

files=`ls *.shp`

mkdir output
for i in $files
do
new=`echo $i | cut -d'.' -f1`
echo "ogr2ogr -f "ESRI Shapefile" -a_srs "EPSG:32734"  output/${new}_WGS84.shp $i"
ogr2ogr -f "ESRI Shapefile" -a_srs "EPSG:32734"  output/${new}_WGS84_UTM34S.shp $i
done
