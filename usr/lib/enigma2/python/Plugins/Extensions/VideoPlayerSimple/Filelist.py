#!/usr/bin/python
# -*- coding: utf-8 -*-
from re import compile as re_compile
from os import path as os_path, listdir
import os, glob, time, random
from Components.MenuList import MenuList
from Components.Harddisk import harddiskmanager
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename, pathExists, fileExists, crawlDirectory
from enigma import RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, \
	eServiceReference, eServiceCenter, gFont, getDesktop
from Tools.LoadPixmap import LoadPixmap

EXTENSIONS = {
		"dts": "music",
		"mp3": "music",
		"wav": "music",
		"wave": "music",
		"wv": "music",
		"oga": "music",
		"ogg": "music",
		"flac": "music",
		"m4a": "music",
		"mp2": "music",
		"m2a": "music",
		"wma": "music",
		"ac3": "music",
		"mka": "music",
		"aac": "music",
		"ape": "music",
		"alac": "music",
		"amr": "music",
		"au": "music",
		"mid": "music",
		"radio": "music",
		"mpg": "movie",
		"vob": "movie",
		"m4v": "movie",
		"mkv": "movie",
		"avi": "movie",
		"divx": "movie",
		"dat": "movie",
		"flv": "movie",
		"mp4": "movie",
		"mov": "movie",
		"wmv": "movie",
		"asf": "movie",
		"3gp": "movie",
		"3g2": "movie",
		"mpeg": "movie",
		"mpe": "movie",
		"rm": "movie",
		"rmvb": "movie",
		"ogm": "movie",
		"ogv": "movie",
		"m2ts": "movie",
		"mts": "movie",
		"ts": "movie",
		"pva": "movie",
		"wtv": "movie",
		"webm": "movie",
		"stream": "movie",
		"m3u": "movie",
		"m3u8": "movie",
		"tv": "movie",
		"e2pls": "movie",
		"pls": "movie",
		"iso": "movie",
		"img": "movie",
		"nrg": "movie",
		"jpg": "picture",
		"jpeg": "picture",
		"jpe": "picture",
		"png": "picture",
		"gif": "picture",
		"bmp": "picture",
		"svg": "picture",
		"webp": "picture",
		"mvi": "picture"
	}

def FileEntryComponent(name, absolute = None, isDir = False, directory = "/", size = 0, timestamp = 0):
	res = [ (absolute, isDir, name) ]
	if (getDesktop(0).size().width() >= 1920):
		if name == "..":
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 53, 0, 1855, 30, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, name))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 53, 0, 1855, 30, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, name))
	else:
		if name == "..":
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 35, 0, 1237, 20, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, name))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 35, 0, 1237, 20, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, name))
	if isDir:
		png = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "extensions/directory.png"))
	else:
		extension = name.split('.')
		extension = extension[-1].lower()
		if extension in EXTENSIONS:
			png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "extensions/" + EXTENSIONS[extension] + ".png"))
		else:
			png = None
	if png is not None:
		if (getDesktop(0).size().width() >= 1920):
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 15, 0, 30, 30, png))
		else:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 10, 0, 20, 20, png))
	return res
class FileList(MenuList):
	def __init__(self, directory, showDirectories = True, showFiles = True, showMountpoints = True, matchingPattern = None, useServiceRef = False, inhibitDirs = False, inhibitMounts = False, isTop = False, enableWrapAround = False, additionalExtensions = None, sort = "date"):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.additional_extensions = additionalExtensions
		self.mountpoints = []
		self.current_directory = None
		self.current_mountpoint = None
		self.useServiceRef = useServiceRef
		self.showDirectories = showDirectories
		self.showMountpoints = showMountpoints
		self.showFiles = showFiles
		self.isTop = isTop
		# example: matching .nfi and .ts files: "^.*\.(nfi|ts)"
		self.matchingPattern = matchingPattern
		self.sort = sort
		self.inhibitDirs = inhibitDirs or []
		self.inhibitMounts = inhibitMounts or []
		self.refreshMountpoints()
		self.changeDir(directory, sort = sort)
		if (getDesktop(0).size().width() >= 1920):
			self.l.setFont(0, gFont("Regular", 27))
			self.l.setItemHeight(33)
		else:
			self.l.setFont(0, gFont("Regular", 18))
			self.l.setItemHeight(23)
		self.serviceHandler = eServiceCenter.getInstance()
	def refreshMountpoints(self):
		self.mountpoints = [os_path.join(p.mountpoint, "") for p in harddiskmanager.getMountedPartitions()]
		self.mountpoints.sort(reverse = True)
	def getMountpoint(self, file):
		file = os_path.join(os_path.realpath(file), "")
		for m in self.mountpoints:
			if file.startswith(m):
				return m
		return False
	def getMountpointLink(self, file):
		if os_path.realpath(file) == file:
			return self.getMountpoint(file)
		else:
			if file[-1] == "/":
				file = file[:-1]
			mp = self.getMountpoint(file)
			last = file
			file = os_path.dirname(file)
			while last != "/" and mp == self.getMountpoint(file):
				last = file
				file = os_path.dirname(file)
			return os_path.join(last, "")
	def getSelection(self):
		if self.l.getCurrentSelection() is None:
			return None
		return self.l.getCurrentSelection()[0]
	def getCurrentEvent(self):
		l = self.l.getCurrentSelection()
		if not l or l[0][1] == True:
			return None
		else:
			return self.serviceHandler.info(l[0][0]).getEvent(l[0][0])
	def getFileList(self):
		return self.list
	def inParentDirs(self, dir, parents):
		dir = os_path.realpath(dir)
		for p in parents:
			if dir.startswith(p):
				return True
		return False
	def changeDir(self, directory, sort = "date", select = None):
		isDir = False
		if sort == "shuffle":
			sort = "default"
			shuffle = True
		else:
			shuffle = False
		self.list = []
		if self.current_directory is None:
			if directory and self.showMountpoints:
				self.current_mountpoint = self.getMountpointLink(directory)
			else:
				self.current_mountpoint = None
		self.current_directory = directory
		directories = []
		files = []
		if directory is None and self.showMountpoints:
			for p in harddiskmanager.getMountedPartitions():
				path = os_path.join(p.mountpoint, "")
				if path not in self.inhibitMounts and not self.inParentDirs(path, self.inhibitDirs):
					self.list.append(FileEntryComponent(name = p.description, absolute = path, isDir = True, directory = directory))
			files = [ ]
			directories = [ ]
		elif directory is None:
			files = [ ]
			directories = [ ]
		elif self.useServiceRef:
			root = eServiceReference(2, 0, directory)
			if self.additional_extensions:
				root.setName(self.additional_extensions)
			serviceHandler = eServiceCenter.getInstance()
			list = serviceHandler.list(root)
			while 1:
				s = list.getNext()
				if not s.valid():
					del list
					break
				if s.flags & s.mustDescent:
					directories.append(s.getPath())
				else:
					files.append(s)
			directories.sort()
			files.sort()
		else:
			if fileExists(directory):
				try:
					files = listdir(directory)
				except:
					files = []
				files.sort()
				tmpfiles = files[:]
				for x in tmpfiles:
					if os_path.isdir(directory + x):
						directories.append(directory + x + "/")
						files.remove(x)
		if directory is not None and self.showDirectories and not self.isTop:
			if directory == self.current_mountpoint and self.showMountpoints:
				self.list.append(FileEntryComponent(name = "<" + "List of storage Devices" + ">", absolute = None, isDir = True, directory = directory))
			elif (directory != "/") and not (self.inhibitMounts and self.getMountpoint(directory) in self.inhibitMounts):
				self.list.append(FileEntryComponent(name = "<" + "Parent directory" + ">", absolute = '/'.join(directory.split('/')[:-2]) + '/', isDir = True, directory = directory))
		date_file_list = []
		if self.showDirectories:
			for x in directories:
				if not (self.inhibitMounts and self.getMountpoint(x) in self.inhibitMounts) and not self.inParentDirs(x, self.inhibitDirs):
					name = x.split('/')[-2]
					file = x
					path = x
					if pathExists(path):
						stats = os.stat(path)
						size = stats[6]
						lastmod_date = time.localtime(stats[8])
					else:
						size = 0
						lastmod_date = 0
					isDir = True
					if sort == "size" or sort == "sizereverse":
						date_file_tuple = size, name, path, file, lastmod_date, isDir
					elif sort == "date" or sort == "datereverse" or sort == "default":
						date_file_tuple = lastmod_date, name, path, file, size, isDir
					elif sort == "alpha" or sort == "alphareverse":
						date_file_tuple = name, lastmod_date, path, file, size, isDir
					date_file_list.append(date_file_tuple)
		if self.showFiles:
			for x in files:
				if self.useServiceRef:
					path = x.getPath()
					name = path.split('/')[-1]
					file = x
					if pathExists(path):
						stats = os.stat(path)
						size = stats[6]
						lastmod_date = time.localtime(stats[8])
					else:
						size = 0
						lastmod_date = 0
					isDir = False
					if sort == "size" or sort == "sizereverse":
						date_file_tuple = size, name, path, file, lastmod_date, isDir
					elif sort == "date" or sort == "datereverse" or sort == "default":
						date_file_tuple = lastmod_date, name, path, file, size, isDir
					elif sort == "alpha" or sort == "alphareverse":
						date_file_tuple = name, lastmod_date, path, file, size, isDir
					date_file_list.append(date_file_tuple)	
				else:
					path = directory + x
					name = x
					if sort == "size" or sort == "sizereverse":
						date_file_tuple = size, name, path, file, lastmod_date, isDir
					elif sort == "date" or sort == "datereverse" or sort == "default":
						date_file_tuple = lastmod_date, name, path, file, size, isDir
					elif sort == "alpha" or sort == "alphareverse":
						date_file_tuple = name, lastmod_date, path, file, size, isDir
					date_file_list.append(date_file_tuple)
		if sort == "datereverse" or sort == "alpha" or sort == "sizereverse" or sort == "date" or sort == "alphareverse" or sort == "size":
			date_file_list.sort()
		if sort == "date" or sort == "alphareverse" or sort == "size":
			date_file_list.reverse()
		if shuffle == True:
			random.shuffle(date_file_list)
		for x in date_file_list:
			if sort == "size" or sort == "sizereverse":
				size = x[0]				
				name = x[1]
				path = x[2]
				file = x[3] 
				timestamp = x[4]				
				isDir = x[5]
			elif sort == "date" or sort == "datereverse" or sort == "default":		
				timestamp = x[0]					
				name = x[1]
				path = x[2]
				file = x[3] 
				size = x[4]
				isDir = x[5]			
			elif sort == "alpha" or sort == "alphareverse":
				name = x[0]
				timestamp = x[1]					
				path = x[2]
				file = x[3] 
				size = x[4]
				isDir = x[5]
			if isDir == True:
				if not (self.inhibitMounts and self.getMountpoint(file) in self.inhibitMounts) and not self.inParentDirs(file, self.inhibitDirs):
					self.list.append(FileEntryComponent(name = name, absolute = file, isDir = isDir, directory = directory, size = size, timestamp = timestamp))
			else:
				if (self.matchingPattern is None) or re_compile(self.matchingPattern).search(path):
					self.list.append(FileEntryComponent(name = name, absolute = file , isDir = isDir, directory = directory, size = size, timestamp = timestamp))
		if self.showMountpoints and len(self.list) == 0:
			self.list.append(FileEntryComponent(name = "nothing connected", absolute = None, isDir = False))
		self.l.setList(self.list)
		if select is not None:
			i = 0
			self.moveToIndex(0)
			for x in self.list:
				p = x[0][0]
				if isinstance(p, eServiceReference):
					p = p.getPath()
				if p == select:
					self.moveToIndex(i)
				i += 1
	def getCurrentDirectory(self):
		return self.current_directory
	def canDescent(self):
		if self.getSelection() is None:
			return False
		return self.getSelection()[1]
	def descent(self):
		if self.getSelection() is None:
			return
		self.changeDir(self.getSelection()[0], select = self.current_directory)
	def gotoParent(self):
		if self.current_directory is not None:
			if self.current_directory == self.current_mountpoint and self.showMountpoints:
				absolute = None
			else:
				absolute = '/'.join(self.current_directory.split('/')[:-2]) + '/'
			self.changeDir(absolute, select = self.current_directory)
	def getName(self):
		if self.getSelection() is None:
			return False
		return self.getSelection()[2]
	def getFilename(self):
		if self.getSelection() is None:
			return None
		x = self.getSelection()[0]
		if isinstance(x, eServiceReference):
			x = x.getPath()
		return x
	def getServiceRef(self):
		if self.getSelection() is None:
			return None
		x = self.getSelection()[0]
		if isinstance(x, eServiceReference):
			return x
		return None
	def execBegin(self):
		harddiskmanager.on_partition_list_change.append(self.partitionListChanged)
	def execEnd(self):
		harddiskmanager.on_partition_list_change.remove(self.partitionListChanged)
	def refresh(self, sort = "default"):
		self.sort = sort
		self.changeDir(self.current_directory, self.sort, self.getFilename())
	def partitionListChanged(self, action, device):
		self.refreshMountpoints()
		if self.current_directory is None:
			self.refresh()
