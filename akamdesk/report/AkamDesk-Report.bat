@echo off
title AkamDesk Report - keep this window open while using the report
echo.
echo  Enter the server password below.
echo  The report opens in your browser a few seconds later.
echo  If the page does not load, wait a moment and press F5.
echo  Close this window when you are done.
echo.
start "" cmd /c "timeout /t 15 > nul & start http://localhost:8088"
ssh -N -L 8088:127.0.0.1:8088 root@desk.akamdata.com
