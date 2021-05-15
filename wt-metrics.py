import PySimpleGUIQt as pygui
import matplotlib.pyplot as plt
import requests,json,time,threading,csv
pygui.theme("SystemDefault1")

def getFrame(url):
	try:
		#append unix time to collected data
		data = json.loads(requests.get("http://"+url+"/state").text)
		data.update({"unixTime":time.time()})
		return data
	except:
		return False

def recordFrame(url,listToRecordTo,selectedMetrics): #this is only defined because it needs to be threaded
	if (frame := getFrame(url)):
		listToRecordTo.append(
			{key:value for key,value in frame.items() if key in selectedMetrics} #filter the frame out to only include selected metrics
		)
	global runningThreadCount
	runningThreadCount-=1

def selectMetricsToCollectPopup(listOptions,listAlreadySelectedValues): #opens "select metrics" dialog window, returns the checked values.
	checkBoxColumn = [[pygui.Checkbox(text=str(option),key=str(option),default=(True if (option in listAlreadySelectedValues) else False))] for option in [option for option in listOptions if option not in ["unixTime"]] ]
	checkWindow = pygui.Window(
		title="Select metrics to be collected",
		layout=[
			[pygui.Text("Selct metrics to be collected")],
			[pygui.Column(checkBoxColumn,size=(300,300),scrollable=True)],
			[pygui.Button("OK"), pygui.Button("Select all"), pygui.Button("Select none")]
		]
	) #create window

	#main window loop
	event,values = checkWindow.read()
	if (event == "Select all"):
		checkWindow.close()
		return selectMetricsToCollectPopup(listOptions,listOptions)
	if (event == "Select none"):
		checkWindow.close()
		return selectMetricsToCollectPopup(listOptions,{})
	if event in [pygui.WIN_CLOSED,"OK"]: #if window is closed or "OK" button pressed
		checkWindow.close() #close window we opened earlier
		return [key for key in values if values[key]]+["unixTime"]

def selectPlotPopup(listOptions):
	optionsColumn = lambda groupID:[[pygui.Radio(text=str(option),key=str(option)+str(groupID),group_id=groupID)] for option in listOptions]
	xColumn = pygui.Column([[pygui.Text("x axis")]]+optionsColumn("x"),size=(300,300),scrollable=True)
	yColumn = pygui.Column([[pygui.Text("y axis")]]+optionsColumn("y"),size=(300,300),scrollable=True)
	plotWindow = pygui.Window(
		title = "Select metrics to be plotted",
		layout = [
			[xColumn,yColumn],
			[pygui.Button("Plot")]
		]
	)

	#main loop
	while True:
		event,values = plotWindow.read()
		if (event == "Plot"):
			#get the keys
			xmetric = "";ymetric = ""
			for (key,value) in values.items():
				if value:
					if key[-1] == "x":
						xmetric = key[:-1]
					else:
						ymetric = key[:-1]
			
			#get the data
			xdata = []
			ydata = []
			for data in [(xdata:=[],xmetric), (ydata:=[],ymetric)]:
				for frame in dataLog:
					data[0].append(frame[data[1]])

			#plot the data
			plt.plot(xdata,ydata)
			plt.xlabel(xmetric)
			plt.ylabel(ymetric)
			plt.show()
	if event == pygui.WIN_CLOSED:
		plotWindow.close()

guiWindow = \
pygui.Window(
	"War Thunder Data Recorder and Grapher",
	[
		[pygui.Text("Source:"),pygui.InputText(default_text="localhost:8111",key="url"),pygui.Button("Select metrics")],
		[pygui.Text("Output file (csv):"),pygui.InputText(default_text="out.csv",key="outfile"),pygui.Text("Logging interval (ms):"),pygui.InputText(default_text="200",key="interval",size=(4,1))],
		[(startButton := pygui.Button("Start")),(saveButton := pygui.Button("Save",disabled=True)),(resetButton := pygui.Button("Reset",disabled=True)),(plotButton := pygui.Button("Graph",disabled=True))]
	]
)

def keylistInDatalog(dataLog):
	keyList = []
	for frame in dataLog:
		for key in list(frame.keys()):
			if key not in keyList:
				keyList.append(key)
	return keyList



#vars used in loop
global dataLog
dataLog = []
global selectedMetrics
selectedMetrics = {"unixTime":True}
global runningThreadCount
runningThreadCount = 0

while True:
	windowEvent,windowValues = guiWindow.Read(timeout=1)

	# select metrics dialog
	if (windowEvent == "Select metrics"):
		if (data := getFrame(windowValues["url"])):
			selectedMetrics = selectMetricsToCollectPopup(list(data.keys()), selectedMetrics)
		else:
			pygui.popup("Error, url does not point to the game")
	
	if (windowEvent == "Start"):
		if int(windowValues["interval"] )< 1:
			pygui.popup("Interval of less than 1ms is not supported.")
		elif (startButton.GetText() == "Start"):
			if len(selectedMetrics) <=1: #if nothing is selected, select everything
				selectedMetrics = list(getFrame(windowValues["url"]).keys())
			startButton.update("Stop") #rename start button to stop becaus we already started
			saveButton.update(text="Save",disabled=True) #disable the save button while recording
			resetButton.update(text="Reset",disabled=True) #disable the reset button while recording
			plotButton.update(text="Graph",disabled=True) #disable the graph button while recording
		else:
			startButton.update("Start")
			saveButton.update(text="Save",disabled=False)
			resetButton.update(text="Reset",disabled=False)
			plotButton.update(text="Graph",disabled=False)

	if startButton.GetText() == "Stop": #while button name is stop, continue spawning threads
		runningThreadCount +=1
		threading._start_new_thread(recordFrame,(windowValues["url"],dataLog,selectedMetrics))
		time.sleep(0.2)

	#save button
	if (windowEvent == "Save"):
		"""	the main probem here is that `http://url/state` returns different keys depending on when its called, so we cant just get the first or last frame and consider all keys present in there. so, we have to loop over every frame and chech if the frame has a key that others dont.
		""" #get fieldnames
		(csvFile := csv.DictWriter((file := open(windowValues["outfile"],"w")),fieldnames=keylistInDatalog(dataLog))).writeheader()
		for frame in dataLog:
			csvFile.writerow(frame)
		file.close()

	if (windowEvent == "Reset"):
		dataLog = []
		resetButton.update(text="Reset",disabled=True)
		loadButton.update(text="Load",disabled=False)

	#plot button
	if (windowEvent == "Graph"):
		selectPlotPopup(keylistInDatalog(dataLog))

	#exit button
	if windowEvent in [pygui.WIN_CLOSED,"Exit"]:
		break
