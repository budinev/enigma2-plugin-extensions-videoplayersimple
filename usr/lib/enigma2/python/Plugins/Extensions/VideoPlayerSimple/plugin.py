# -*- coding: utf-8 -*-

# VideoPlayerSimple by mrvica, based on Homeys MediaPlayerDeluxe -> MediaCenter -> BMediaCenter, MovieSelection, MediaPlayer and others

from .Filelist import FileList
from Components.config import config, configfile, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, ConfigSelection, ConfigSelectionNumber, getConfigListEntry
from Components.Label import Label
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer as OrigMoviePlayer
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, pathExists, SCOPE_MEDIA
from Components.Button import Button
from Components.ActionMap import ActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import eTimer, getDesktop, iPlayableService, eServiceReference, eServiceCenter, ePicLoad
from Components.ConfigList import ConfigListScreen
from Components.Console import Console
from Screens.InfoBarGenerics import InfoBarAudioSelection, InfoBarSubtitleSupport, InfoBarCueSheetSupport, InfoBarNotifications, InfoBarSeek
from Screens.MessageBox import MessageBox
from Screens.MinuteInput import MinuteInput
from Components.Pixmap import Pixmap
from Components.AVSwitch import AVSwitch
from Components.Sources.StaticText import StaticText
from os import stat as os_stat, path as os_path, popen as os_popen, remove as os_remove, walk as os_walk
from time import strftime as time_strftime
from time import localtime as time_localtime

config.plugins.videoplayersimple = ConfigSubsection()
config.plugins.videoplayersimple.lastDirVideo = ConfigText(default=resolveFilename(SCOPE_MEDIA))
config.plugins.videoplayersimple.playnext = ConfigYesNo(default=False)
config.plugins.videoplayersimple.autoplay = ConfigYesNo(default=False)
config.plugins.videoplayersimple.playdelay = ConfigSelectionNumber(100, 3000, 100, default = 500)
config.plugins.videoplayersimple.leftrightskipping = ConfigSelectionNumber(1, 9, 1, default = 5)
config.plugins.videoplayersimple.resume = ConfigYesNo(default=False)
config.plugins.videoplayersimple.pictureplayer = ConfigYesNo(default=False)
config.plugins.videoplayersimple.sortmode = ConfigSubsection()
sorts = [("default", _("default")),
	("alpha", _("alphabet")),
	("alphareverse", _("alphabet backward")),
	("date", _("date")),
	("datereverse", _("date backward")),
	("size", _("size")),
	("sizereverse", _("size backward")),
	("shuffle", _("shuffle"))]
config.plugins.videoplayersimple.sortmode.enabled = ConfigSelection(sorts)

class MoviePlayer(OrigMoviePlayer):
	def __init__(self, session, service):
		self.session = session
		self.WithoutStopClose = False
		OrigMoviePlayer.__init__(self, self.session, service)
	
	def doEofInternal(self, playing):
		if not self.execing:
			return
		if not playing:
			return
		self.leavePlayer()
	
	def leavePlayer(self):
		self.close()

	def showMovies(self):
		self.WithoutStopClose = True
		self.close()
	
	def movieSelected(self, service):
		self.leavePlayer(self.de_instance)

	def __onClose(self):                                                        
		if not(self.WithoutStopClose):                                      
			self.session.nav.playService(self.lastservice)              

class VideoPlayerSimple_Config(Screen, ConfigListScreen):
	if (getDesktop(0).size().width() >= 1920):
		skin = """
			<screen name="VideoPlayerSetup" position="center,center" size="842,510" title="Video Player Simple Setup">
				<widget name="config" position="15,15" size="810,375" font="Regular;30" itemHeight="42" scrollbarMode="showOnDemand" />
				<widget name="key_red" position="8,420" size="197,60" zPosition="2" font="Regular;30" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="white" />
				<widget name="key_green" position="218,420" size="197,60" zPosition="2" font="Regular;30" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="white" />
				<widget name="key_yellow" position="428,420" size="197,60" zPosition="2" font="Regular;30" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="white" />
				<widget name="key_blue" position="638,420" size="197,60" zPosition="2" font="Regular;30" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="white" />
			</screen>"""
	else:
		skin = """
			<screen name="VideoPlayerSetup" position="center,center" size="559,335" title="Video Player Simple Setup">
				<widget name="config" position="10,10" size="540,250" scrollbarMode="showOnDemand" />
				<widget name="key_red" position="5,280" size="130,40" zPosition="2" font="Regular;21" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="white" />
				<widget name="key_green" position="145,280" size="130,40" zPosition="2" font="Regular;21" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="white" />
				<widget name="key_yellow" position="285,280" size="130,40" zPosition="2" font="Regular;21" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="white" />
				<widget name="key_blue" position="425,280" size="130,40" zPosition="2" font="Regular;21" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="white" />
			</screen>"""
	
	def __init__(self, session):
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.save,
			"red": self.close,
			"cancel": self.close
		}, -2)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")

		cfglist = []
		cfglist.append(getConfigListEntry(_("Auto Play"), config.plugins.videoplayersimple.autoplay))
		cfglist.append(getConfigListEntry(_("Play Delay"), config.plugins.videoplayersimple.playdelay))
		cfglist.append(getConfigListEntry(_("Play Next on EOF and Auto Play enabled"), config.plugins.videoplayersimple.playnext))
		cfglist.append(getConfigListEntry(_("Left / Right (or long press) skipping in secs"), config.plugins.videoplayersimple.leftrightskipping))
		cfglist.append(getConfigListEntry(_("Resume playback from last played position"), config.plugins.videoplayersimple.resume))
		cfglist.append(getConfigListEntry(_("Use internal Picture Player"), config.plugins.videoplayersimple.pictureplayer))
		cfglist.append(getConfigListEntry(_("Filelist Sorting"), config.plugins.videoplayersimple.sortmode.enabled))
		ConfigListScreen.__init__(self, cfglist, session)

	def save(self):
		ConfigListScreen.keySave(self)
		configfile.save()
		
class VideoPlayerSimple(Screen, InfoBarAudioSelection, InfoBarSubtitleSupport, InfoBarCueSheetSupport, InfoBarNotifications, InfoBarSeek):

	STATE_PLAYING = 1
	STATE_PAUSED = 2
	ALLOW_SUSPEND = True
	FLAG_CENTER_DVB_SUBS = 2048
	ENABLE_RESUME_SUPPORT = config.plugins.videoplayersimple.resume.value

	if (getDesktop(0).size().width() >= 1920):
		skin = """
			<screen position="fill" title="Video Player Simple" backgroundColor="#4512121e" flags="wfNoBorder">
				<widget name="currentfolder" valign="center" position="9,1026" size="1731,54" backgroundColor="#4512121e" foregroundColor="#00ffaa00" font="Regular;27" noWrap="1"/>
				<widget source="session.CurrentService" halign="right" valign="center" render="Label" position="1718,1026" size="150,54" font="Regular;27" backgroundColor="#4512121e" foregroundColor="#00ffaa00">
					<convert type="ServicePosition">Remaining,Negate,ShowHours</convert>
				</widget>
				<widget name="thn" position="1170,180" size="720,405"/>
				<widget source="label" render="Label" position="1170,600" size="720,270" zPosition="5" transparent="1" font="Regular;30"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VideoPlayerSimple/blue_fhd.png" position="1889,1040" size="26,26" alphatest="on"/>
				<widget name="filelist" position="3,6" size="1908,1026" backgroundColor="#4512121e" foregroundColor="#f0f0f0" scrollbarMode="showOnDemand" enableWrapAround="1"/>
			</screen>"""
	else:
		skin = """
			<screen position="fill" title="Video Player Simple" backgroundColor="#4512121e" flags="wfNoBorder">
				<widget name="currentfolder" valign="center" position="6,692" size="1154,30" backgroundColor="#4512121e" foregroundColor="#00ffaa00" font="Regular;18" noWrap="1"/>
				<widget source="session.CurrentService" halign="right" valign="center" render="Label" position="1145,692" size="100,30" font="Regular;18" backgroundColor="#4512121e" foregroundColor="#00ffaa00">
					<convert type="ServicePosition">Remaining,Negate,ShowHours</convert>
				</widget>
				<widget name="thn" position="774,120" size="480,270"/>
				<widget source="label" render="Label" position="774,400" size="480,180" zPosition="5" transparent="1" font="Regular;20"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VideoPlayerSimple/blue_hd.png" position="1256,698" size="20,20" alphatest="on"/>
				<widget name="filelist" position="2,3" size="1272,690" backgroundColor="#4512121e" foregroundColor="#f0f0f0" scrollbarMode="showOnDemand" enableWrapAround="1"/>
			</screen>"""
		
	def __init__(self, session, args = None):
		self.skin = VideoPlayerSimple.skin
		Screen.__init__(self, session)
		InfoBarAudioSelection.__init__(self)
		InfoBarCueSheetSupport.__init__(self, actionmap = "MediaPlayerCueSheetActions")
		InfoBarNotifications.__init__(self)
		InfoBarSubtitleSupport.__init__(self)
		self.isVisible = True
		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self["currentfolder"] = Label("")
		self["thn"] = Pixmap()
		self["label"] = StaticText("")
		back15 = lambda: self.seekRelative(-1, config.seek.selfdefined_13.value * 90000)
		fwd15 = lambda: self.seekRelative(1, config.seek.selfdefined_13.value * 90000)
		back60 = lambda: self.seekRelative(-1, config.seek.selfdefined_46.value * 90000)
		fwd60 = lambda: self.seekRelative(1, config.seek.selfdefined_46.value * 90000)
		back300 = lambda: self.seekRelative(-1, config.seek.selfdefined_79.value * 90000)
		fwd300 = lambda: self.seekRelative(1, config.seek.selfdefined_79.value * 90000)
		back = lambda: self.seekRelative(-1, int(config.plugins.videoplayersimple.leftrightskipping.value) * 90000)
		fwd = lambda: self.seekRelative(1, int(config.plugins.videoplayersimple.leftrightskipping.value)* 90000)
		back10 = lambda: self.seekRelative(-1, 10 * 90000)
		fwd10 = lambda: self.seekRelative(1, 10 * 90000)
		back900 = lambda: self.seekRelative(-1, 900 * 90000)
		fwd900 = lambda: self.seekRelative(1, 900 * 90000)
		self.state = self.STATE_PLAYING
		self.onPlayStateChanged = [ ]
		
		self["myactions"] = ActionMap(["VideoPlayerActions"],
		{
			"vp_ok": self.ok,
			"vp_cancel": self.exit,
			"vp_cancellong": self.exitlong,
			"vp_menu": self.visibility,
			"vp_red": self.deleteFile,
			"vp_green": self.playMoviePlayer,
			"vp_blue": self.ConfigMenu,
			"vp_playpauseService": self.playpauseService,
			"vp_1": back15, 
			"vp_3": fwd15,
			"vp_4": back60,
			"vp_6": fwd60,
			"vp_7": back300,
			"vp_9": fwd300,
			"vp_2": self.go5pageUp,
			"vp_5": self.go5pageDown,
			"vp_8": self.listbegin,
			"vp_0": self.listend,
			"vp_showMovies": self.updatelist,
			"vp_seekBack": back900,
			"vp_seekFwd": fwd900,
			"vp_left": back,
			"vp_right": fwd,
			"vp_up": self.up,
			"vp_down": self.down,
			"vp_prevService": back10,
			"vp_nextService": fwd10,
			"vp_movePrev": self.up,
			"vp_moveNext": self.down,
			"vp_prevBouquet": self.chDown,
			"vp_nextBouquet": self.chUp,
			"vp_seekFwdManual": self.seekFwdManual,
			"vp_seekBackManual": self.seekBackManual,
			"vp_info": self.Info,
			"vp_shuffle": self.hotkeyShuffle,
			"vp_default": self.hotkeyDefault,
			"vp_name": self.hotkeyName,
			"vp_namereverse": self.hotkeyNamereverse,
			"vp_size": self.hotkeySize,
			"vp_sizereverse": self.hotkeySizereverse,
			"vp_date": self.hotkeyDate,
			"vp_datereverse": self.hotkeyDatereverse,
			"vp_displayHelp": self.showHelp,
			"vp_stoptv": self.stopTV,
			"vp_playtv": self.playTV,
			"vp_togglethumb": self.toggleThumb,
			"vp_leavePlayer": self.StopPlayback
		}, -1)

		currDir = config.plugins.videoplayersimple.lastDirVideo.value
		if not pathExists(currDir):
			currDir = "/"
		sort = config.plugins.videoplayersimple.sortmode.enabled.value
		self.filelist = []
		self["filelist"] = []
		self.filelist = FileList(currDir, useServiceRef = True, showDirectories = True, showFiles = True, matchingPattern = "(?i)^.*\.(dts|mp3|wav|wave|wv|oga|ogg|flac|m4a|mp2|m2a|wma|ac3|mka|aac|ape|alac|amr|au|mid|mpg|mpeg|mpe|vob|m4v|mkv|avi|divx|dat|flv|mp4|mov|wmv|asf|3gp|3g2|rm|rmvb|ogm|ogv|m2ts|mts|ts|pva|wtv|webm|stream|iso|img|nrg|jpg|jpeg|jpe|png|bmp|gif|svg|mvi)", additionalExtensions = "4198:jpg 4198:jpeg 4198:jpe 4198:png 4198:bmp 4198:gif 4198:svg 4198:mvi", sort = sort)
		self["filelist"] = self.filelist
		
		self.filelist.onSelectionChanged.append(self.selectionChanged)
		self["currentfolder"].setText(self.filelist.getCurrentDirectory())
		
		self.VideoTimer = eTimer()
		self.VideoTimer.callback.append(self.showVideo)

		self.ThumbTimer = eTimer()
		self.ThumbTimer.callback.append(self.showThumb)
		
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)

		self.onLayoutFinish.append(self.setConf)

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{ iPlayableService.evEOF: self.__evEOF, })

	def showPic(self, picInfo=""):
		ptr = self.picload.getData()
		if ptr is not None:
			self["thn"].instance.setPixmap(ptr.__deref__())
			self["thn"].show()
		text = picInfo.split('\n',1)
		self["label"].setText(text[1])
		if self.isVisible == False:
			self.visibility()
			return

	def showThumb(self):
		if not self.filelist.canDescent():
			if self.filelist.getCurrentDirectory() and self.filelist.getFilename():
				if self.picload.getThumbnail(self.filelist.getFilename()) == 1:
					self.ThumbTimer.start(500, True)

	def toggleThumb(self):
		if self["label"].getText() == "":
			self.showThumb()
		else:
			self["label"].setText("")
			self["thn"].hide()

	def setConf(self, retval=None):
		#width, height, aspectRatio, as, useCache, resizeType, bg_str, auto_orientation
		self.picload.setPara((self["thn"].instance.size().width(), self["thn"].instance.size().height(), 1, 1, 0, 0, "#FF2C2C39", 1))

	def seekRelative(self, direction, amount):
		seekable = self.getSeek()
		if seekable is None:
			return
		seekable.seekRelative(direction, amount)

	def getSeek(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None
		seek = service.seek()
		if seek is None or not seek.isCurrentlySeekable():
			return None
		return seek

	def playpauseService(self):
		if self.state == self.STATE_PLAYING:
			self.pauseService()
		elif self.state == self.STATE_PAUSED:
			self.unPauseService()

	def pauseService(self):
		if self.state == self.STATE_PLAYING:
			self.setSeekState(self.STATE_PAUSED)

	def unPauseService(self):
		if self.state == self.STATE_PAUSED:
			self.setSeekState(self.STATE_PLAYING)

	def setSeekState(self, wantstate):
		service = self.session.nav.getCurrentService()
		if service is None:
			return False
		pauseable = service.pause()
		if pauseable is None:
			self.state = self.STATE_PLAYING
		if pauseable is not None:
			if wantstate == self.STATE_PAUSED:
				pauseable.pause()
				self.state = self.STATE_PAUSED
			elif wantstate == self.STATE_PLAYING:
				pauseable.unpause()
				self.state = self.STATE_PLAYING
		for c in self.onPlayStateChanged:
			c(self.state)
		return True

	def __evEOF(self):
		if (config.plugins.videoplayersimple.autoplay.value == True) and (config.plugins.videoplayersimple.playnext.value == True):
			self.down()
		else:
			self.session.nav.playService(self.oldService)

	def seekFwdManual(self):
		self.session.openWithCallback(self.fwdSeekTo, MinuteInput)

	def fwdSeekTo(self, minutes):
		self.seekRelative(1, minutes * 60 * 90000)

	def seekBackManual(self):
		self.session.openWithCallback(self.rwdSeekTo, MinuteInput)

	def rwdSeekTo(self, minutes):
		self.seekRelative(-1, minutes * 60 * 90000)

	def showHelp(self):
		if self.isVisible == False:
			self.visibility()
			return
		self.session.open(MessageBox, '%s' % 'Supported formats :\ndts, mp3, wav, wave, wv, oga, ogg, flac, m4a, mp2, m2a\nwma, ac3, mka, aac, ape, alac, amr, au, mid, mpg, vob\nm4v, mkv, avi, divx, dat, flv, mp4, mov, wmv, asf, 3gp, 3g2\nmpeg, mpe, rm, rmvb, ogm, ogv, m2ts, mts, ts, pva, wtv\nwebm, stream\nPicture : jpg, jpeg, jpe, png, bmp, gif, svg, mvi\nDVD : VIDEO_TS, iso, img, nrg', MessageBox.TYPE_INFO, close_on_any_key=True)
		self.session.open(MessageBox, '%s' % 'Picture Player external:\nThumbs:\nLeft/Right/Up/Down : direction\nOK : choose file\nInfo : File/Exif info\n\nPicture Full View:\nRed/Left : previous picture\nBlue/Right : next picture\nGreen/Yellow : play/pause\nInfo : File/Exif info\nMenu : Picture Player menu\n\nPicture Player internal:\nLeft/Right : previous, next picture\nUp : file info\nDown/Exit : leave', MessageBox.TYPE_INFO, close_on_any_key=True)
		self.session.open(MessageBox, '%s' % 'Audio (yellow) : audio track\nSubtitle : subtitles\nFav, Pvr, Video, Filelist : refresh file list (as set in config)\nTxt : sort name, long : sort name reverse\nRecord : sort size, long : sort size reverse\nTimer : sort date, long : sort date reverse\nRadio : shuffle (reshuffle), long : sort default\nStop : stop playing\nPause : pause/unpause playing\nInfo : File/Dir/System Info, Event View if available (only .ts)\nTV : play TV, long : stop TV\nExit : leave video player, long : leave player without conformation\nHelp : this help', MessageBox.TYPE_INFO, close_on_any_key=True)
		self.session.open(MessageBox, '%s' % '1/3, 4/6, 7/9 : 15 secs, 60 secs, 300 secs (config) : skipping\n<prev/next> 10 secs, long press (repeated) : skipping\n<</>> 15 mins : skipping\n<</>> long press : manual seek in minutes\nLeft/Right 1-9 secs skipping, long press : repeated skipping\nUp/Down/|</>| : up, down in file list, play previous, next in auto play\nCH+/CH- : one page up, down\n2/5 : 5 pages up, down\n8/0 : list begin, list end\nOK : play (not needed in auto play), long : hide file list\nRed : delete file (use with caution)\nGreen : play with E2 movie player\nBlue : Config\nMenu : hide/show file list, long : hide/show thumb', MessageBox.TYPE_INFO, close_on_any_key=True)

	def selectionChanged(self):
		self["currentfolder"].setText(self.filelist.getCurrentDirectory())
		
	def up(self):
		self.filelist.up()
		self.filename = self.filelist.getFilename()
		if self.filename != None:
			if not self.filelist.canDescent() and self.filename.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg')):
				self.ThumbTimer.start(500, True)
			elif not self.filelist.canDescent() and self.filename.lower().endswith(('.mvi', '.iso', '.img', '.nrg')):
				pass
			else:
				self["label"].setText("")
				self["thn"].hide()
				self.VideoTimer.start(int(config.plugins.videoplayersimple.playdelay.value), True)
		
	def down(self):
		self.filelist.down()
		self.filename = self.filelist.getFilename()
		if self.filename != None:
			if not self.filelist.canDescent() and self.filename.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg')):
				self.ThumbTimer.start(500, True)
			elif not self.filelist.canDescent() and self.filename.lower().endswith(('.mvi', '.iso', '.img', '.nrg')):
				pass
			else:
				self["label"].setText("")
				self["thn"].hide()
				self.VideoTimer.start(int(config.plugins.videoplayersimple.playdelay.value), True)
	
	def chUp(self):
		self.filelist.pageUp()

	def chDown(self):
		self.filelist.pageDown()

	def go5pageUp(self):
		for x in range(5):
			self.filelist.pageUp()

	def go5pageDown(self):
		for x in range(5):
			self.filelist.pageDown()

	def listbegin(self):
		self.filelist.moveToIndex(0)

	def listend(self):
		idx = len(self.filelist.list)
		self.filelist.moveToIndex(idx - 1)

	def showVideo(self):
		if config.plugins.videoplayersimple.autoplay.value == False:
			return
		else:
			if self.filelist.getServiceRef() is not None and self.filelist.getServiceRef().type != 4198:
				self.session.nav.stopService()
				self.session.nav.playService(self.filelist.getServiceRef())
	
	def ok(self):
		if self.isVisible == False:
			self.visibility()
			return
		self.VideoTimer.stop()
		if self.filelist.canDescent():
			self.filelist.descent()
		else:
			self.filename = self.filelist.getFilename()
			if self.filename != None:
				try:
					if self.filename.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg')):
						if config.plugins.videoplayersimple.pictureplayer.value == False:
							from Components.FileList import FileList as Filelist
							from Plugins.Extensions.PicturePlayer import ui
							self.tempfl = Filelist("/", matchingPattern = "(?i)^.*\.(jpeg|jpg|jpe|png|bmp|gif|svg)")
							self.tempfl.changeDir(self.filelist.getCurrentDirectory())
							#self.session.openWithCallback(self.callbackView, ui.Pic_Thumb, self.tempfl.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())
							self.session.openWithCallback(self.callbackView, ui.Pic_Thumb, self.tempfl.getFileList(), 0, self.filelist.getCurrentDirectory())
							#self.session.openWithCallback(self.callbackView, ui.Pic_Full_View, self.tempfl.getFileList(), 0, self.filelist.getCurrentDirectory())
							#this doesn´t work, any idea !!!
							#self.session.openWithCallback(self.callbackView, ui.Pic_Thumb, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())
							#self.session.openWithCallback(self.callbackView, ui.Pic_Full_View, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())
						else:
							self.session.openWithCallback(self.callbackView, PictureExplorer, self.filename, self.filelist.getCurrentDirectory())
		
				except Exception, e:
					print "[Video Player Simple] error Picture Player:", e

				try:
					if self.filename.lower().endswith('.mvi'):
						self.session.nav.stopService()
						cmd = "/usr/bin/showiframe '%s'" % self.filename
						Console().ePopen(cmd)
				except Exception, e:
					print "showiframe error:", e

				try:
					if self.filename.lower().endswith(('.iso', '.img', '.nrg')) or self.filename.endswith('VIDEO_TS/'):
						self.session.nav.stopService()
						from Screens import DVD
						path = self.filename
						self.session.open(DVD.DVDPlayer, dvd_filelist=[path])
						return
				except Exception, e:
					print "DVD Player error:", e

			if self.filelist.getServiceRef() is not None and self.filelist.getServiceRef().type != 4198:
				self.session.nav.stopService()
				self.session.nav.playService(self.filelist.getServiceRef())
		
	def callbackView(self, val=0):
		if val > 0:
			self.filelist.moveToIndex(val)
		self.session.nav.playService(self.oldService)

	def playMoviePlayer(self):
		if self.isVisible == False:
			self.visibility()
			return
		self.VideoTimer.stop()
		self.filename = self.filelist.getFilename()
		if self.filename != None:
			if self.filename.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg', '.mvi', '.iso', '.img', '.nrg')):
				pass
			else:
				if self.filelist.getServiceRef() is not None:
					self.session.open(MoviePlayer, self.filelist.getServiceRef())
			
	def visibility(self, force=1):
		if self.isVisible == True:
			self.isVisible = False
			self.hide()
		else:
			self.isVisible = True
			self.show()

	def updatelist(self):
		sort = config.plugins.videoplayersimple.sortmode.enabled.value
		self.filelist.refresh(sort)
		#self.filelist.moveToIndex(0)

	def hotkeyShuffle(self):
		sort = "shuffle"
		self.filelist.refresh(sort)
		#self.filelist.moveToIndex(0)

	def hotkeyDefault(self):
		sort = "default"
		self.filelist.refresh(sort)
		#self.filelist.moveToIndex(0)

	def hotkeyName(self):
		sort = "alpha"
		self.filelist.refresh(sort)
		#self.filelist.moveToIndex(0)
	
	def hotkeyNamereverse(self):
		sort = "alphareverse"
		self.filelist.refresh(sort)
		#self.filelist.moveToIndex(0)

	def hotkeySize(self):
		sort = "size"
		self.filelist.refresh(sort)
		#self.filelist.moveToIndex(0)

	def hotkeySizereverse(self):
		sort = "sizereverse"
		self.filelist.refresh(sort)
		#self.filelist.moveToIndex(0)

	def hotkeyDate(self):
		sort = "date"
		self.filelist.refresh(sort)
		#self.filelist.moveToIndex(0)

	def hotkeyDatereverse(self):
		sort = "datereverse"
		self.filelist.refresh(sort)
		#self.filelist.moveToIndex(0)
	
	def ConfigMenu(self):
		if self.isVisible == False:
			self.visibility()
			return
		self.session.openWithCallback(self.updatelist, VideoPlayerSimple_Config)

	def StopPlayback(self):
		self.VideoTimer.stop()
		self.session.nav.stopService()
		self.session.nav.playService(self.oldService)
			
		if self.isVisible == False:
			self.show()
			self.isVisible = True
	
	def stopTV(self):
		if self.isVisible == False:
			self.visibility()
			return
		self.session.nav.stopService()

	def playTV(self):
		if self.isVisible == False:
			self.visibility()
			return
		self.session.nav.playService(self.oldService)
	
	def exit(self):
		if self.isVisible == False:
			self.show()
			self.isVisible = True
		self.session.openWithCallback(self.exitCallback, MessageBox, _("Exit video player?"))

	def exitCallback(self, answer):
		if answer:
			if self.isVisible == False:
				self.visibility()
				return
			if self.filelist.getCurrentDirectory() is None:
				config.plugins.videoplayersimple.lastDirVideo.value = "/"
			else:
				config.plugins.videoplayersimple.lastDirVideo.value = self.filelist.getCurrentDirectory()
			self.session.nav.playService(self.oldService)
			config.plugins.videoplayersimple.save()
			self.close()
		else:
			pass

	def exitlong(self):
		if self.filelist.getCurrentDirectory() is None:
			config.plugins.videoplayersimple.lastDirVideo.value = "/"
		else:
			config.plugins.videoplayersimple.lastDirVideo.value = self.filelist.getCurrentDirectory()
		self.session.nav.playService(self.oldService)
		config.plugins.videoplayersimple.save()
		self.close()

	def dirContentSize(self, directory, humanized = True):
		size = 0
		for dirpath, dirnames, filenames in os_walk(directory):
			for f in filenames:
				fp = os_path.join(dirpath, f)
				size += os_path.getsize(fp) if os_path.isfile(fp) else 0
		if humanized:
			return self.Humanizer(size)
		return size
	
	def Humanizer(self, size):
		for index,count in enumerate([_('B'),_('KB'),_('MB'),_('GB')]):
			if size < 1024.0:
				return "%3.2f %s" % (size, count) if index else "%d %s" % (size, count)
			size /= 1024.0
		return "%3.2f %s" % (size, _('TB'))
	
	def Info(self):
		if self.filelist.canDescent():
			if self.filelist.getSelectionIndex()!=0:
				curSelDir = self.filelist.getSelection()[0]
				dircontentsize = self.dirContentSize(curSelDir)
				dir_stats = os_stat(curSelDir)
				dir_infos = "Directory:  %s" % curSelDir+"\n\n"
				#dir_infos = dir_infos+"Size:  "+str("%s B" % "{:,d}".format(dir_stats.st_size)+ "    " +self.Humanizer(dir_stats.st_size))+"\n"
				dir_infos = dir_infos+"Size with subdir(s):  %s" % str(dircontentsize)+"\n"
				dir_infos = dir_infos+"Last modified:  "+time_strftime("%d.%m.%Y,  %H:%M:%S",time_localtime(dir_stats.st_mtime))+"\n"
				dir_infos = dir_infos+"Mode:  %s" % oct(dir_stats.st_mode)[-3:]
				dei = self.session.open(MessageBox, dir_infos, MessageBox.TYPE_INFO)
				dei.setTitle(_("Dir Info"))
			else:
				dei = self.session.open(MessageBox, ScanSysem_str(), MessageBox.TYPE_INFO)
				dei.setTitle(_("Flash / Memory Info"))
		else:
			curSelFile = self.filelist.getFilename()
			file_stats = os_stat(curSelFile)
			file_infos = "File:  %s" % curSelFile+"\n\n"
			file_infos = file_infos+"Size:  "+str("%s B" % "{:,d}".format(file_stats.st_size)+ "    " +self.Humanizer(file_stats.st_size))+"\n"
			file_infos = file_infos+"Last modified:  "+time_strftime("%d.%m.%Y,  %H:%M:%S",time_localtime(file_stats.st_mtime))+"\n"
			file_infos = file_infos+"Mode:  %s" % oct(file_stats.st_mode)[-3:]
			dei = self.session.open(MessageBox, file_infos, MessageBox.TYPE_INFO)
			dei.setTitle(_("File Info"))
			if curSelFile.endswith(".ts"):
				from Screens.EventView import EventViewSimple
				from ServiceReference import ServiceReference
				serviceref = eServiceReference("1:0:0:0:0:0:0:0:0:0:" + curSelFile)
				serviceHandler = eServiceCenter.getInstance()
				info = serviceHandler.info(serviceref)
				evt = info.getEvent(serviceref)
				if evt:
					self.session.open(EventViewSimple, evt, ServiceReference(serviceref))

	def deleteFile(self):
		self.delpath = self.filelist.getFilename()
		if self.delpath is not None: 
			delfilename = self.delpath.rsplit("/",1)[1]
		self.service = self.filelist.getServiceRef()
		if self.service is None:
			return
		if self.service.type != 4098 and self.session.nav.getCurrentlyPlayingServiceReference() is not None:
			if self.service == self.session.nav.getCurrentlyPlayingServiceReference():
				#self.session.nav.playService(None)
				self.StopPlayback()
		serviceHandler = eServiceCenter.getInstance()
		offline = serviceHandler.offlineOperations(self.service)
		info = serviceHandler.info(self.service)
		name = info and info.getName(self.service)
		result = False
		if offline is not None:
			# simulate first
			if not offline.deleteFromDisk(1):
				result = True
		if result == True:
			self.session.openWithCallback(self.deleteConfirmed_offline, MessageBox, _("This file will be permanently deleted:\n\n'%s'\n\n('%s')\n\nAre you shure?") % (name, delfilename), default = False)
		else:
			if delfilename.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg', '.mvi', '.iso', '.img', '.nrg')):
				if self.filelist.getSelectionIndex()!=0:
					if delfilename is "":
						pass
					else:
						self.delname = self.delpath
						self.session.openWithCallback(self.deleteFileConfirmed, MessageBox, _("This file will be permanently deleted:\n\n'%s'\n\nAre you shure?") % delfilename, default = False)
				else:
					pass
			else:
				self.session.open(MessageBox, _("You cannot delete this!"), MessageBox.TYPE_ERROR, close_on_any_key=True)

	def deleteConfirmed_offline(self, confirmed):
		if confirmed:
			serviceHandler = eServiceCenter.getInstance()
			offline = serviceHandler.offlineOperations(self.service)
			result = False
			if offline is not None:
				# really delete!
				if not offline.deleteFromDisk(0):
					result = True
			if result == False:
				self.session.open(MessageBox, _("Delete failed!"), MessageBox.TYPE_ERROR)
			else:
				currdir = self.filelist.getCurrentDirectory()
				self.filelist.changeDir(currdir)
				if self.isVisible == False:
					self.visibility()
					return
				self.session.nav.playService(self.oldService)
				self.updatelist()

	def deleteFileConfirmed(self, confirmed):
		if confirmed:
			if os_path.exists (self.delname) is True:
				os_remove(self.delname)
			else:
				self.session.open(MessageBox,_("non-existent file, could not delete\n\n( %s )" % self.delname), MessageBox.TYPE_WARNING)
			currdir = self.filelist.getCurrentDirectory()
			self.filelist.changeDir(currdir)
			if self.isVisible == False:
				self.visibility()
				return
			self.session.nav.playService(self.oldService)
			self.updatelist()

def ScanSysem_str():
	try:
		ret = ""
		out_line = os_popen("uptime").readline()
		ret = ret  + "at" + out_line + "\n"
		out_lines = []
		out_lines = os_popen("cat /proc/meminfo | grep Mem").readlines()
		for lidx in range(len(out_lines)):
			ret = ret + out_lines[lidx]
		ret = ret + "\n"
		out_lines = []
		out_lines = os_popen("df -h").readlines()
		for lidx in range(len(out_lines)):
			ret = ret + out_lines[lidx]
		ret = ret + "\n"
		out_lines = []
		out_lines = os_popen("top -b -n 1 | head -n 2 | grep CPU:").readlines()
		for lidx in range(len(out_lines)):
			ret = ret + out_lines[lidx]
		ret = ret + "\n"
		return ret
	except:
		return "N/A"

class PictureExplorer(Screen):
	if (getDesktop(0).size().width() >= 1920):
		skin="""
			<screen flags="wfNoBorder" position="fill" title="Picture-Explorer" backgroundColor="#ffffffff">
				<widget name="Picture" position="fill" zPosition="1"/>
				<widget name="State" font="Regular;27" position="15,8" size="1890,35" noWrap="1" foregroundColor="#ffaa00" zPosition="5"/>
			</screen>"""
	else:
		skin="""
			<screen flags="wfNoBorder" position="fill" title="Picture-Explorer" backgroundColor="#ffffffff">
				<widget name="Picture" position="fill" zPosition="1"/>
				<widget name="State" font="Regular;18" position="10,5" size="1260,24" noWrap="1" foregroundColor="#ffaa00" zPosition="5"/>
			</screen>"""

	def __init__(self, session, whatPic = None, whatDir = None):
		#self.skin = PictureExplorer.skin
		Screen.__init__(self, session)
		self.session = session
		self.whatPic = whatPic
		self.whatDir = whatDir
		self.picList = []
		self.Pindex = 0
		self.EXscale = (AVSwitch().getFramebufferScale())
		self.EXpicload = ePicLoad()
		self["Picture"] = Pixmap()
		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self["State"] = Label('loading... '+self.whatPic)
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"],
		{
			"ok": self.info,
			"back": self.close,
			"up": self.info,
			"down": self.close,
			"left": self.Pleft,
			"right": self.Pright
		}, -1)
		self.EXpicload.PictureData.get().append(self.DecodeAction)
		self.onLayoutFinish.append(self.Show_Picture)

	def Show_Picture(self):
		if self.whatPic is not None:
			self.EXpicload.setPara([self["Picture"].instance.size().width(), self["Picture"].instance.size().height(), self.EXscale[0], self.EXscale[1], 0, 1, "#FF2C2C39", 1])
			self.EXpicload.startDecode(self.whatPic)
		if self.whatDir is not None:
			pidx = 0
			for (root, dirs, files) in os_walk(self.whatDir):
				for name in sorted(files):
					if name.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg')):
						self.picList.append(name)
						if name in self.whatPic:
							self.Pindex = pidx
						pidx = pidx + 1

	def DecodeAction(self, pictureInfo=""):
		if self.whatPic is not None:
			self["State"].setText("ready...")
			self["State"].visible = False
			ptr = self.EXpicload.getData()
			self["Picture"].instance.setPixmap(ptr.__deref__())
			self.session.nav.playService(self.oldService)

	def Pright(self):
		if len(self.picList) > 2:
			if self.Pindex < (len(self.picList)-1):
				self.Pindex += 1
				self.whatPic = self.whatDir + str(self.picList[self.Pindex])
				self["State"].visible = True
				self["State"].setText('('+str(self.Pindex+1)+'/'+str(len(self.picList))+')'+'  '+'loading... '+self.whatPic)
				self.EXpicload.startDecode(self.whatPic)
			else:
				if self.Pindex == (len(self.picList)-1):
					self.Pindex = -1
					self["State"].setText("wait...")
					#self["State"].visible = False
					#self.session.open(MessageBox,_('No more picture-files.'), MessageBox.TYPE_INFO, close_on_any_key=True)
					#self.session.open(MessageBox,_('No more picture-files.'), MessageBox.TYPE_INFO, timeout=2)

	def Pleft(self):
		if len(self.picList) > 2:
			if self.Pindex > 0:
				self.Pindex -= 1
				self.whatPic = self.whatDir + str(self.picList[self.Pindex])
				self["State"].visible = True
				self["State"].setText('('+str(self.Pindex+1)+'/'+str(len(self.picList))+')'+'  '+'loading... '+self.whatPic)
				self.EXpicload.startDecode(self.whatPic)
			else:
				if self.Pindex == 0:
					self.Pindex = (len(self.picList))
					#self["State"].setText("wait...")
					#self["State"].visible = False
					#self.session.open(MessageBox,_('No more picture-files.'), MessageBox.TYPE_INFO, close_on_any_key=True)
					#self.session.open(MessageBox,_('No more picture-files.'), MessageBox.TYPE_INFO, timeout=2)
	
	def info(self):
		if self["State"].visible:
			self["State"].setText("wait...")
			self["State"].visible = False
		else:
			self["State"].visible = True
			self["State"].setText('('+str(self.Pindex+1)+'/'+str(len(self.picList))+')'+'  '+self.whatPic)

def main(session, **kwargs):
	session.open(VideoPlayerSimple)

def Plugins(**kwargs):
	return [
		PluginDescriptor(name = "Video Player Simple", description = "Simple Video Player", icon="plugin.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main),
		PluginDescriptor(name = "Video Player Simple", description = "Simple Video Player", icon="plugin.png", where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main)]
