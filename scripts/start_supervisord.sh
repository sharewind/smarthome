#!/bin/bash
cd dirname(dirname(__FILE__))
pkill supervisord
supervisord
