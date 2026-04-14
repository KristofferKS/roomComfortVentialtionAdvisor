#!/bin/bash
rm output.csv
curl -L http://130.225.37.202:9080/comtek-6-631.csv -o output.csv
