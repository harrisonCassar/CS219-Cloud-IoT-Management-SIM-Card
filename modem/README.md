# WIP
Will contain all SIM-related code, including the Python modem emulator.

# Local Environment Setup
```python3 -m venv env```

```source env/bin/activate```

```pip install requirements.txt```

# Installing applet
Download javacard applet repo:

```git clone https://github.com/JinghaoZhao/eSIM-Applet-dev.git```

```git checkout -b dev-send-data```

```cd eSIM-Applet-dev```

Build the cap file

```./gradlew buildJavaCard  --info --rerun-tasks```

Remove applet from physical SIM card:

```java -jar ./GlobalPlatformPro/gp.jar --delete 010203040506070809```

Installing applet to physical SIM card:

```java -jar ./GlobalPlatformPro/gp.jar --install ./applet/build/javacard/esim.cap --default```

# Run
```source env/bin/activate```

```python3 modem.py```