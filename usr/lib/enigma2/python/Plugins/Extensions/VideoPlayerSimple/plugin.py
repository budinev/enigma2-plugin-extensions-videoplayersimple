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
from enigma import eTimer, getDesktop, iPlayableService, eServiceReference, eServiceCenter, ePicLoad, iServiceInformation, eListboxPythonMultiContent, gFont
from Components.ConfigList import ConfigListScreen
from Components.Console import Console
from Screens.InfoBarGenerics import InfoBarAudioSelection, InfoBarSubtitleSupport, InfoBarCueSheetSupport, InfoBarNotifications, InfoBarSeek
from Screens.MessageBox import MessageBox
from Screens.MinuteInput import MinuteInput
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.Pixmap import Pixmap
# from Components.AVSwitch import AVSwitch
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from os import stat as os_stat, path as os_path, popen as os_popen, remove as os_remove, walk as os_walk, system as os_system, error as os_error
from time import strftime as time_strftime
from time import localtime as time_localtime
import re

config.plugins.videoplayersimple = ConfigSubsection()
config.plugins.videoplayersimple.lastDirVideo = ConfigText(default=resolveFilename(SCOPE_MEDIA))
config.plugins.videoplayersimple.playnext = ConfigYesNo(default=False)
config.plugins.videoplayersimple.autoplay = ConfigYesNo(default=False)
config.plugins.videoplayersimple.playdelay = ConfigSelectionNumber(100, 3000, 100, default = 500)
config.plugins.videoplayersimple.leftrightskipping = ConfigSelectionNumber(1, 9, 1, default = 5)
config.plugins.videoplayersimple.resume = ConfigYesNo(default=False)
config.plugins.videoplayersimple.pictureplayer = ConfigYesNo(default=False)
config.plugins.videoplayersimple.dvdmenu = ConfigYesNo(default=True)
config.plugins.videoplayersimple.thumbssize = ConfigYesNo(default=True)
config.plugins.videoplayersimple.iptvmovieplayer = ConfigYesNo(default=True)
config.plugins.videoplayersimple.iptvdescription = ConfigYesNo(default=True)
config.plugins.videoplayersimple.sortmode = ConfigSubsection()
sorts = [("default", "default"),
	("alpha", "alphabet"),
	("alphareverse", "alphabet backward"),
	("date", "date"),
	("datereverse", "date backward"),
	("size", "size"),
	("sizereverse", "size backward"),
	("shuffle", "shuffle")]
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
		self.close()
	
	def movieSelected(self, service):
		self.leavePlayer(self.de_instance)

	def __onClose(self):
		if not(self.WithoutStopClose):
			self.session.nav.playService(self.lastservice)

class VideoPlayerSimple_Config(Screen, ConfigListScreen):
	if (getDesktop(0).size().width() >= 1920):
		skin = """
			<screen name="VideoPlayerSetup" position="center,center" size="915,630" title="Video Player Simple Setup">
				<widget name="config" position="15,15" size="885,540" font="Regular;30" itemHeight="42" scrollbarMode="showOnDemand" />
				<widget name="key_red" position="8,555" size="217,60" zPosition="2" font="Regular;30" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="white" />
				<widget name="key_green" position="233,555" size="217,60" zPosition="2" font="Regular;30" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="white" />
				<widget name="key_yellow" position="458,555" size="217,60" zPosition="2" font="Regular;30" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="white" />
				<widget name="key_blue" position="683,555" size="217,60" zPosition="2" font="Regular;30" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="white" />
			</screen>"""
	else:
		skin = """
			<screen name="VideoPlayerSetup" position="center,center" size="610,400" title="Video Player Simple Setup">
				<widget name="config" position="10,10" size="590,340" scrollbarMode="showOnDemand" />
				<widget name="key_red" position="5,350" size="145,40" zPosition="2" font="Regular;21" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="white" />
				<widget name="key_green" position="155,350" size="145,40" zPosition="2" font="Regular;21" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="white" />
				<widget name="key_yellow" position="305,350" size="145,40" zPosition="2" font="Regular;21" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="white" />
				<widget name="key_blue" position="455,350" size="145,40" zPosition="2" font="Regular;21" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="white" />
			</screen>"""
	
	def __init__(self, session):
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.save,
			"red": self.close,
			"cancel": self.close
		}, -2)

		self["key_red"] = Button("Cancel")
		self["key_green"] = Button("OK")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")

		cfglist = []
		cfglist.append(getConfigListEntry("Auto Play", config.plugins.videoplayersimple.autoplay))
		cfglist.append(getConfigListEntry("Play Delay in ms", config.plugins.videoplayersimple.playdelay))
		cfglist.append(getConfigListEntry("Play Next on EOF", config.plugins.videoplayersimple.playnext))
		cfglist.append(getConfigListEntry("Left / Right (or long press) skipping in secs", config.plugins.videoplayersimple.leftrightskipping))
		cfglist.append(getConfigListEntry("Use internal Picture Player", config.plugins.videoplayersimple.pictureplayer))
		cfglist.append(getConfigListEntry("Open VIDEO_TS as DVD Menu", config.plugins.videoplayersimple.dvdmenu))
		cfglist.append(getConfigListEntry("Filelist Sorting", config.plugins.videoplayersimple.sortmode.enabled))
		cfglist.append(getConfigListEntry("Resume playback from last played position", config.plugins.videoplayersimple.resume))
		cfglist.append(getConfigListEntry("Thumbs size in filelist smaller", config.plugins.videoplayersimple.thumbssize))
		cfglist.append(getConfigListEntry("Play IPTV services with Movie Player", config.plugins.videoplayersimple.iptvmovieplayer))
		cfglist.append(getConfigListEntry("Description for IPTV bouguet services (.tv, .radio) after (:)", config.plugins.videoplayersimple.iptvdescription))
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

	if config.plugins.videoplayersimple.thumbssize.value == True:
		posxhd = 774
		posyhd = 120
		sizexhd = 480
		sizeyhd = 270
		posxfhd = 1170
		posyfhd = 180
		sizexfhd = 720
		sizeyfhd = 405
		textposxhd = 774
		textposyhd = 400
		textsizexhd = 480
		textsizeyhd = 180
		textposxfhd = 1170
		textposyfhd = 600
		textsizexfhd = 720
		textsizeyfhd = 270
	else:
		posxhd = 574
		posyhd = 50
		sizexhd = 680
		sizeyhd = 370
		posxfhd = 870
		posyfhd = 105
		sizexfhd = 1020
		sizeyfhd = 555
		textposxhd = 574
		textposyhd = 430
		textsizexhd = 480
		textsizeyhd = 180
		textposxfhd = 870
		textposyfhd = 675
		textsizexfhd = 720
		textsizeyfhd = 270

	if (getDesktop(0).size().width() >= 1920):
		skin = """
			<screen position="fill" title="Video Player Simple" backgroundColor="#4512121e" flags="wfNoBorder">
				<widget name="currentfolder" valign="center" position="9,1026" size="1731,54" backgroundColor="#4512121e" foregroundColor="#00ffaa00" font="Regular;27" noWrap="1"/>
				<widget source="session.CurrentService" halign="right" valign="center" render="Label" position="1718,1026" size="150,54" font="Regular;27" backgroundColor="#4512121e" foregroundColor="#00ffaa00">
					<convert type="ServicePosition">Remaining,Negate,ShowHours</convert>
				</widget>
				<widget name="thn" position="%d,%d" size="%d,%d" zPosition="5"/>
				<widget source="label" render="Label" position="%d,%d" size="%d,%d" zPosition="5" transparent="1" font="Regular;30"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VideoPlayerSimple/blue_fhd.png" position="1889,1040" size="26,26" alphatest="on"/>
				<widget name="filelist" position="3,6" size="1908,1026" backgroundColor="#4512121e" foregroundColor="#f0f0f0" scrollbarMode="showOnDemand" enableWrapAround="1"/>
			</screen>""" % ( posxfhd, posyfhd, sizexfhd, sizeyfhd, textposxfhd, textposyfhd, textsizexfhd, textsizeyfhd )
	else:
		skin = """
			<screen position="fill" title="Video Player Simple" backgroundColor="#4512121e" flags="wfNoBorder">
				<widget name="currentfolder" valign="center" position="6,692" size="1154,30" backgroundColor="#4512121e" foregroundColor="#00ffaa00" font="Regular;18" noWrap="1"/>
				<widget source="session.CurrentService" halign="right" valign="center" render="Label" position="1145,692" size="100,30" font="Regular;18" backgroundColor="#4512121e" foregroundColor="#00ffaa00">
					<convert type="ServicePosition">Remaining,Negate,ShowHours</convert>
				</widget>
				<widget name="thn" position="%d,%d" size="%d,%d" zPosition="5"/>
				<widget source="label" render="Label" position="%d,%d" size="%d,%d" zPosition="5" transparent="1" font="Regular;20"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VideoPlayerSimple/blue_hd.png" position="1256,698" size="20,20" alphatest="on"/>
				<widget name="filelist" position="2,3" size="1272,690" backgroundColor="#4512121e" foregroundColor="#f0f0f0" scrollbarMode="showOnDemand" enableWrapAround="1"/>
			</screen>""" % ( posxhd, posyhd, sizexhd, sizeyhd, textposxhd, textposyhd, textsizexhd, textsizeyhd )
		
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
			"vp_searchfile": self.searchFile,
			"vp_cutlistedit": self.openCutListEditor,
			"vp_deletecuts": self.deleteCuts,
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
		self.filelist = FileList(currDir, useServiceRef = True, showDirectories = True, showFiles = True, matchingPattern = "(?i)^.*\.(dts|mp3|wav|wave|wv|oga|ogg|flac|m4a|mp2|m2a|wma|ac3|mka|aac|ape|alac|amr|au|mid|mpg|mpeg|mpe|vob|m4v|mkv|avi|divx|dat|flv|mp4|mov|wmv|asf|3gp|3g2|rm|rmvb|ogm|ogv|m2ts|mts|ts|pva|wtv|webm|stream|iso|img|nrg|jpg|jpeg|jpe|png|bmp|gif|svg|mvi|m3u|m3u8|tv|radio|e2pls|pls|txt|webp)", additionalExtensions = "4198:jpg 4198:jpeg 4198:jpe 4198:png 4198:bmp 4198:gif 4198:svg 4198:mvi 4198:m3u 4198:m3u8 4198:tv 4198:radio 4198:e2pls 4198:pls 4198:txt 4198:webp", sort = sort)
		self["filelist"] = self.filelist
		
		self.filelist.onSelectionChanged.append(self.selectionChanged)
		self["currentfolder"].setText(self.filelist.getCurrentDirectory())
		# self["currentfolder"].setText(str(self.filelist.getCurrentDirectory()).strip('None') + "  ( " + str(len(self.filelist.getFileList())) + ' file(s) )')
		
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
	
	def toggleThumb(self, force = 1):
		if self.isVisible == True:
			self.isVisible = False
			self["label"].setText("")
			self["thn"].hide()
		else:	
			self.isVisible = True
			self["thn"].show()

	def setConf(self, retval=None):
		# width, height, aspectRatio, as, useCache, resizeType, bg_str, auto_orientation
		self.picload.setPara((self["thn"].instance.size().width(), self["thn"].instance.size().height(), 1, 1, False, 0, "#FF2C2C39", 1))

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
		if (config.plugins.videoplayersimple.autoplay.value == True):
			self.down()
		elif (config.plugins.videoplayersimple.playnext.value == True):
			self.down()
			if self.filelist.getServiceRef() is not None and self.filelist.getServiceRef().type != 4198:
				self.session.nav.stopService()
				self.session.nav.playService(self.filelist.getServiceRef())
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
		self.session.open(MessageBox, '%s' % 'Supported formats :\ndts, mp3, wav, wave, wv, oga, ogg, flac, m4a, mp2, m2a\nwma, ac3, mka, aac, ape, alac, amr, au, mid, mpg, vob\nm4v, mkv, avi, divx, dat, flv, mp4, mov, wmv, asf, 3gp, 3g2\nmpeg, mpe, rm, rmvb, ogm, ogv, m2ts, mts, ts, pva, wtv\nwebm, stream, m3u, m3u8, e2pls, pls\ntxt (open http(s) links, view small txt files)\nuserbouquet.*.tv\nuserbouquet.*.radio\nPicture : jpg, jpeg, jpe, png, bmp, gif, svg, mvi\nwebp (as converted to jpg)\nDVD : VIDEO_TS, iso, img, nrg', MessageBox.TYPE_INFO, close_on_any_key=True)
		self.session.open(MessageBox, '%s' % 'Picture Player external:\nThumbs:\nLeft/Right/Up/Down : direction\nOK : choose file\nInfo : File/Exif info\n\nPicture Full View:\nRed/Left : previous picture\nBlue/Right : next picture\nGreen/Yellow : play/pause\nInfo : File/Exif info\nMenu : Picture Player menu\n\nPicture Player internal:\nLeft/Right : previous, next picture\nUp : file info\nDown/Exit : leave', MessageBox.TYPE_INFO, close_on_any_key=True)
		self.session.open(MessageBox, '%s' % 'Audio (yellow) : audio track\nSubtitle : subtitles\nFav, Pvr, Video, Filelist : refresh file list (as set in config)\nTxt : sort name, long : sort name reverse\nTxt : in .txt mode show long line wrapped\nTxt : in .m3u(8), .tv, .radio list search for entries (expt)\nRecord : sort size, long : sort size reverse\nTimer : sort date, long : sort date reverse\nRadio : shuffle (reshuffle), long : sort default\nStop : stop playing\nPause : pause/unpause playing\nInfo : File/Dir/System Info, Event View if available (only .ts)\nTV : play TV, long : stop TV\nEpg long : search for file(s) in the file list\nBack : invoke Cutlist editor, long : delete .cuts file\nExit : leave video player, long : leave player without conformation\nHelp : this help', MessageBox.TYPE_INFO, close_on_any_key=True)
		self.session.open(MessageBox, '%s' % '1/3, 4/6, 7/9 : 15 secs, 60 secs, 300 secs (e2 config) : skipping\n<prev/next> 10 secs, long press (repeated) : skipping\n<prev/next> in .radio bouquet mode show stream titles, 7/9 : OK\n<</>> 15 mins : skipping\n<</>> long press : manual seek in minutes\nLeft/Right 1-9 secs skipping, long press : repeated skipping\nUp/Down/|</>| : up, down in file list, play previous, next in auto play\nCH+/CH- : one page up, down\n2/5 : 5 pages up, down\n8/0 : list begin, list end\nOK : play (not needed in auto play), long : hide file list\nRed : delete file / empty .Trash can (use with caution)\nGreen : play with E2 movie player\nBlue : Config\nMenu : hide/show file list, long : hide/show thumb', MessageBox.TYPE_INFO, close_on_any_key=True)

	def selectionChanged(self):
		self["currentfolder"].setText(self.filelist.getCurrentDirectory())
		# self["currentfolder"].setText(str(self.filelist.getCurrentDirectory()).strip('None') + "  ( " + str(len(self.filelist.getFileList())) + ' file(s) )')
		self.ThumbTimer.stop()
		
	def up(self):
		self.filelist.up()
		self.filename = self.filelist.getFilename()
		if self.filename != None:
			if not self.filelist.canDescent() and self.filename.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg')):
				self.ThumbTimer.start(500, True)
			elif not self.filelist.canDescent() and self.filename.lower().endswith(('.mvi', '.iso', '.img', '.nrg', '.m3u', '.m3u8', '.tv', '.radio', '.e2pls', '.pls', '.txt')):
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
			elif not self.filelist.canDescent() and self.filename.lower().endswith(('.mvi', '.iso', '.img', '.nrg', '.m3u', '.m3u8', '.tv', '.radio', '.e2pls', '.pls', '.txt')):
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
		
		self.filename = self.filelist.getFilename()
		if self.filename != None:
			try:
				if self.filename.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg')):
					if config.plugins.videoplayersimple.pictureplayer.value == False:
						from Plugins.Extensions.PicturePlayer import ui
						# this doesn�t work, any idea !!!
						# cannot concatenate 'str' and 'eServiceReference'
						# self.session.openWithCallback(self.callbackView, ui.Pic_Thumb, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())
						# self.session.openWithCallback(self.callbackView, ui.Pic_Full_View, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())
						# workaround
						from Components.FileList import FileList as Filelist
						self.tempfl = Filelist("/", matchingPattern = "(?i)^.*\.(jpeg|jpg|jpe|png|bmp|gif|svg)")
						self.filelist.refresh("alpha")
						# self.filelist.refresh("shuffle")
						self.tempfl.changeDir(self.filelist.getCurrentDirectory())
						self.session.openWithCallback(self.callbackView, ui.Pic_Thumb, self.tempfl.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())
						# self.session.openWithCallback(self.callbackView, ui.Pic_Full_View, self.tempfl.getFileList(), 0, self.filelist.getCurrentDirectory())
					else:
						self.session.openWithCallback(self.callbackView, PictureExplorer, self.filename, self.filelist.getCurrentDirectory())
			except Exception as e:
				print("[Video Player Simple] error Picture Player:", e)

			try:
				if self.filename.lower().endswith('.mvi'):
					self.session.nav.stopService()
					cmd = "/usr/bin/showiframe '%s'" % self.filename
					Console().ePopen(cmd)
			except Exception as e:
				print("showiframe error:", e)

			try:
				if self.filename.lower().endswith('.webp'):
					self.session.openWithCallback(self.convertConfirmed, MessageBox, "This file cannot be displayed:\n\n'%s'\n\nDo you want to convert it to jpg ?" % (self.filename), list=[("No", False), ("Yes", True)])
			except:
				pass
			
			try:
				if self.filename.lower().endswith(('.m3u', '.m3u8')):
					self.session.nav.stopService()
					self.session.open(m3uOpen, self.filename)
			except Exception as e:
				print("m3u(8) file error:", e)

			try:
				if self.filename.lower().endswith('.e2pls'):
					self.session.nav.stopService()
					self.session.open(e2plsOpen, self.filename)
			except Exception as e:
				print("e2pls file error:", e)

			try:
				if self.filename.lower().endswith('.txt'):
					self.session.nav.stopService()
					self.session.open(txtOpen, self.filename)
			except Exception as e:
				print("txt file error:", e)

			try:
				if self.filename.lower().endswith('.pls'):
					self.session.nav.stopService()
					self.session.open(plsOpen, self.filename)
			except Exception as e:
				print("pls file error:", e)
			
			try:
				if self.filename.lower().endswith('.tv'):
					self.session.nav.stopService()
					self.session.open(userbouquetTvOpen, self.filename)
			except Exception as e:
				print("userbouquet .tv file error:", e)

			try:
				if self.filename.lower().endswith('.radio'):
					self.session.nav.stopService()
					self.session.open(userbouquetRadioOpen, self.filename)
			except Exception as e:
				print("userbouquet .radio file error:", e)

			try:
				if self.filename.lower().endswith(('.iso', '.img', '.nrg')) or self.filename.upper().endswith('VIDEO_TS/'):
					if self.filename.upper().endswith('VIDEO_TS/') and config.plugins.videoplayersimple.dvdmenu.value == True:
						path = os_path.split(self.filename.rstrip('/'))[0]
					if self.filename.upper().endswith('VIDEO_TS/') and config.plugins.videoplayersimple.dvdmenu.value == False:
						pass
					else:
						path = self.filename
					self.session.nav.stopService()
					from Screens import DVD
					self.session.open(DVD.DVDPlayer, dvd_filelist=[path])
					return
			except Exception as e:
				print("DVD Player error:", e)
		
		if self.filelist.canDescent():
			self.filelist.descent()
		
		if self.filelist.getServiceRef() is not None and self.filelist.getServiceRef().type != 4198:
			self.session.nav.stopService()
			self.session.nav.playService(self.filelist.getServiceRef())
	
	def convertConfirmed(self, confirmed):
		if confirmed:
			if os_path.exists ("/usr/bin/ffmpeg") is True:
				self.filename2 = self.filename[:-4] + 'jpg'
				cmd = "/usr/bin/ffmpeg -y -i '%s' -preset ultrafast '%s'" % (self.filename, self.filename2)
				Console().ePopen(cmd)
				if os_path.exists (self.filename2) is False:
					print("this build of ffmpeg does not include a webp codec")
					self.session.open(MessageBox, "this build of ffmpeg does not include a webp codec", MessageBox.TYPE_ERROR)
				else:
					print(("converting .webp to .jpg -> '%s'" % cmd))
					self.session.open(MessageBox, "finished converting:\n\n'%s'\n\nto\n\n'%s'" % (self.filename, self.filename2), MessageBox.TYPE_INFO, timeout=5)
					self.updatelist()
			else:
				print("ffmpeg not installed")
				self.session.open(MessageBox, "conversion failed:\n\nffmpeg not installed", MessageBox.TYPE_ERROR)
		else:
			self.session.open(MessageBox, "conversion not performed !", MessageBox.TYPE_INFO, timeout=5)
		
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
			if self.filename.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg', '.mvi', '.iso', '.img', '.nrg', '.m3u', '.m3u8', '.tv', '.radio', '.e2pls', '.pls', '.txt')):
				pass
			else:
				if self.filelist.getServiceRef() is not None:
					self.session.open(MoviePlayer, self.filelist.getServiceRef())
			
	def visibility(self, force = 1):
		if self.isVisible == True:
			self.isVisible = False
			self.hide()
		else:
			self.isVisible = True
			self.show()

	def updatelist(self):
		sort = config.plugins.videoplayersimple.sortmode.enabled.value
		self.filelist.refresh(sort)
		# self.filelist.moveToIndex(0)

	def hotkeyShuffle(self):
		sort = "shuffle"
		self.filelist.refresh(sort)
		# self.filelist.moveToIndex(0)

	def hotkeyDefault(self):
		sort = "default"
		self.filelist.refresh(sort)
		# self.filelist.moveToIndex(0)

	def hotkeyName(self):
		sort = "alpha"
		self.filelist.refresh(sort)
		# self.filelist.moveToIndex(0)
	
	def hotkeyNamereverse(self):
		sort = "alphareverse"
		self.filelist.refresh(sort)
		# self.filelist.moveToIndex(0)

	def hotkeySize(self):
		sort = "size"
		self.filelist.refresh(sort)
		# self.filelist.moveToIndex(0)

	def hotkeySizereverse(self):
		sort = "sizereverse"
		self.filelist.refresh(sort)
		# self.filelist.moveToIndex(0)

	def hotkeyDate(self):
		sort = "date"
		self.filelist.refresh(sort)
		# self.filelist.moveToIndex(0)

	def hotkeyDatereverse(self):
		sort = "datereverse"
		self.filelist.refresh(sort)
		# self.filelist.moveToIndex(0)

	def searchFile(self):
		if self.isVisible == False:
			self.visibility()
			return
		self.session.openWithCallback(self.filterFile, VirtualKeyBoard, title="Search for file(s) in the file list...", text='')
		self.session.open(MessageBox, "Search for file(s) in the file list !\npress Filelist / Pvr / Video / Fav\nto return to full file list again\nenter a search string:", MessageBox.TYPE_INFO, timeout=7)

	def filterFile(self, retval):
		if retval:
			try:
				search = retval
				print('keyboard input -> %s' % search)
				newList = []
				for file_tuple in self["filelist"].list:
					name = file_tuple
					if search.lower() in str(name).lower():
						newList.append(file_tuple)
				if len(newList) < 1:
					self.session.open(MessageBox, "No file(s) found!!!", MessageBox.TYPE_INFO, timeout=5)
					return
				else:
					self["filelist"].l.setList(newList)
					self["filelist"].moveToIndex(0)
					self["currentfolder"].setText(str(self.filelist.getCurrentDirectory()) + "  ( " + str(len(newList)) + ' file(s) found )')
			except Exception as e:
				self.session.open(MessageBox, "Error", MessageBox.TYPE_INFO, timeout=5)
				print(e)
		else:
			self.updatelist()

	def openCutListEditor(self):
		self.filename = self.filelist.getFilename()
		if self.filename.lower().endswith('.ts'):
			try:
				from Plugins.Extensions.CutListEditor import ui
				self.session.open(ui.CutListEditor, self.filelist.getServiceRef())
			except:
				self.session.open(MessageBox, "could not load Cutlist editor", MessageBox.TYPE_ERROR)
		else:
			self.session.open(MessageBox, "Cutlist editor, only .ts files supported", MessageBox.TYPE_INFO, timeout=5)

	def deleteCuts(self):
		if self.isVisible == False:
			self.visibility()
			return
		self.filename = self.filelist.getFilename()
		if self.filename.lower().endswith('.ts'):
			self.filename = self.filename + ('.cuts')
			self.session.nav.playService(self.oldService)
			self.session.openWithCallback(self.removeCuts, MessageBox, "If you experience problems with the file duration\n(e.g. after cutting) you may delete the .cuts file,\nIt will be recreated after playing the video file again\n\nAre you shure to delete?\n'%s'" % self.filename, list=[("No", False), ("Yes", True)])

	def removeCuts(self, confirmed):
		if confirmed:
			try:
				os_remove(self.filename)
				self.session.open(MessageBox, "file .cuts deleted, updating list", MessageBox.TYPE_INFO, timeout=5)
				self.updatelist()
			except:
				self.session.open(MessageBox, "could not delete .cuts file or non-existent", MessageBox.TYPE_ERROR)
		else:
			self.session.open(MessageBox, ".cuts file not deleted", MessageBox.TYPE_INFO, timeout=5)

	def ConfigMenu(self):
		if self.isVisible == False:
			self.visibility()
			return
		self.session.openWithCallback(self.updatelist, VideoPlayerSimple_Config)

	def StopPlayback(self):
		self.VideoTimer.stop()
		self.ThumbTimer.stop()
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
		self.session.openWithCallback(self.exitCallback, MessageBox, "Exit video player?")

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
		for index,count in enumerate(['B', 'KB', 'MB', 'GB']):
			if size < 1024.0:
				return "%3.2f %s" % (size, count) if index else "%d %s" % (size, count)
			size /= 1024.0
		return "%3.2f %s" % (size, 'TB')

	def createResolution(self, serviceInfo):
		codec_data = {
			-1: "N/A",
			0: "MPEG2",
			1: "AVC",
			2: "H263",
			3: "VC1",
			4: "MPEG4-VC",
			5: "VC1-SM",
			6: "MPEG1",
			7: "HEVC",
			8: "VP8",
			9: "VP9",
			10: "XVID",
			11: "N/A 11",
			12: "N/A 12",
			13: "DIVX 3.11",
			14: "DIVX 4",
			15: "DIVX 5",
			16: "AVS",
			17: "N/A 17",
			18: "VP6",
			19: "N/A 19",
			20: "N/A 20",
			21: "SPARK",
			40: "AVS2",
		}
		xres = serviceInfo.getInfo(iServiceInformation.sVideoWidth)
		if xres == -1:
			return ""
		yres = serviceInfo.getInfo(iServiceInformation.sVideoHeight)
		mode = ("i", "p", " ")[serviceInfo.getInfo(iServiceInformation.sProgressive)]
		fps = (serviceInfo.getInfo(iServiceInformation.sFrameRate) + 500) // 1000
		if not fps:
			try:
				fps = (int(open("/proc/stb/vmpeg/0/framerate", "r").read()) + 500) // 1000
			except:
				pass
		codec = codec_data.get(serviceInfo.getInfo(iServiceInformation.sVideoType), "N/A")
		if xres and yres == 65535:
			return ("N/A")
		else:
			return "%sx%s%s%s,  %s" % (xres, yres, mode, fps, codec)

	def getLength(self):
		seek = self.getSeek()
		if seek is None:
			return None
		length = seek.getLength()
		if length[0]:
			return 0
		return length[1]

	def Info(self):
		if self.isVisible == False:
			self.visibility()
			return
		if self.filelist.canDescent():
			if self.filelist.getSelectionIndex()!=0:
				curSelDir = self.filelist.getSelection()[0]
				dircontentsize = self.dirContentSize(curSelDir)
				dir_stats = os_stat(curSelDir)
				dir_infos = "Directory:  %s" % curSelDir+"\n\n"
				# dir_infos = dir_infos+"Size:  "+str("%s B," % "{:,d}".format(dir_stats.st_size)+ "    " +self.Humanizer(dir_stats.st_size))+"\n"
				dir_infos = dir_infos+"Size with subdir(s):  %s" % str(dircontentsize)+"\n"
				dir_infos = dir_infos+"Last modified:  "+time_strftime("%d.%m.%Y,  %H:%M:%S",time_localtime(dir_stats.st_mtime))
				# dir_infos = dir_infos+"Mode:  %s" % oct(dir_stats.st_mode)[-3:]
				dei = self.session.open(MessageBox, dir_infos, MessageBox.TYPE_INFO)
				dei.setTitle("Dir Info")
			else:
				dei = self.session.open(MessageBox, ScanSysem_str(), MessageBox.TYPE_INFO)
				dei.setTitle("Flash / Memory Info")
		else:
			res = ""
			dur = 0
			cover = '/tmp/cover_temp.jpg'
			curSelFile = self.filelist.getFilename()
			service = self.session.nav.getCurrentService()
			
			if service:
				serviceInfo = service and service.info()
				if serviceInfo:
					res = self.createResolution(serviceInfo)
					try:
						dur = self.getLength() // 90000
					except:
						pass

			file_stats = os_stat(curSelFile)
			file_infos = "Dir:  %s ,    %s file(s)" % (str(self.filelist.getCurrentDirectory()), str(len(self.filelist.getFileList())))+"\n\n"
			# file_infos = "File:  %s" % curSelFile+"\n\n"
			file_infos = file_infos+"File:  %s" % curSelFile+"\n\n"
			file_infos = file_infos+"Size:  "+str("%s B," % "{:,d}".format(file_stats.st_size)+ "    " +self.Humanizer(file_stats.st_size))+"\n"
			file_infos = file_infos+"Last modified:  "+time_strftime("%d.%m.%Y,  %H:%M:%S",time_localtime(file_stats.st_mtime))+"\n"
			# file_infos = file_infos+"Mode:  %s" % oct(file_stats.st_mode)[-3:]+"\n"
			file_infos = file_infos+"Duration:  %d:%02d:%02d" % (dur//3600, dur%3600//60, dur%60) + "\n"
			file_infos = file_infos+"Video resolution:\n%s" % str(res)
			dei = self.session.open(MessageBox, file_infos, MessageBox.TYPE_INFO)
			dei.setTitle("Dir / File Info")

			if curSelFile.lower().endswith('.mp3'):
				try:
					from mutagen.id3 import ID3, ID3NoHeaderError
					from mutagen.mp3 import MP3, HeaderNotFoundError
					from mutagen import File
				except ImportError:
					self.session.open(MessageBox, "install mutagen package !\nopkg install python-mutagen\nor\nopkg install python3-mutagen", MessageBox.TYPE_INFO, timeout=5)
					print(("\ninstall mutagen package, 'opkg install python-mutagen' or 'opkg install python3-mutagen'\n"))
				
				try:
					os_remove(cover)
				except os_error:
					pass
				
				try:
					self.audio = ID3(curSelFile)
				except ID3NoHeaderError:
					return

				try:
					self.audio = MP3(curSelFile)
				except HeaderNotFoundError:
					return

				try: mArtist = str(self.audio['TPE1'].text[0])
				except: mArtist = ""
				try: mTitle = str(self.audio['TIT2'].text[0])
				except: mTitle = ""
				try: mAlbum = str(self.audio['TALB'].text[0])
				except: mAlbum = ""
				try: mYear = str(self.audio['TDRC'].text[0])
				except: mYear = ""
				try: mGenre = str(self.audio['TCON'].text[0])
				except: mGenre = ""
				try: mBand = str(self.audio['TPE2'].text[0])
				except: mBand = ""
				try: mCompose = str(self.audio['TCOM'].text[0])
				except: mCompose = ""
				try: mTrack = str(self.audio['TRCK'].text[0])
				except: mTrack = ""
				# try: mComment = str(self.audio['COMM'].text[0])
				# except: mComment = ""
				try: mBitrate = str(self.audio.info.bitrate)
				except: mBitrate = ""
				try: mSamplerate = str(self.audio.info.sample_rate)
				except: mSamplerate = ""
				# try: mLength = str(self.audio.info.length)
				# except: mLength = ""

				# print(("Artist: '%s'" % self.audio['TPE1'].text[0]))
				# print(("Title: '%s'" % self.audio['TIT2'].text[0]))
				# print(("Album: '%s'" % self.audio['TALB'].text[0]))
				
				file_infos = "File:  %s" % curSelFile+"\n\n"
				file_infos = file_infos+"Artist:  %s" % mArtist + "\n"
				file_infos = file_infos+"Title:  %s" % mTitle + "\n"
				file_infos = file_infos+"Album:  %s" % mAlbum + "\n"
				file_infos = file_infos+"Year:  %s" % mYear + "\n"
				file_infos = file_infos+"Genre:  %s" % mGenre + "\n"
				file_infos = file_infos+"Band:  %s" % mBand + "\n"
				file_infos = file_infos+"Compose:  %s" % mCompose + "\n"
				file_infos = file_infos+"Track:  %s" % mTrack + "\n"
				# file_infos = file_infos+"Comment:  %s" % mComment + "\n"
				file_infos = file_infos+"Bitrate:  %s Bps ( bytes per second )" % mBitrate + "\n"
				file_infos = file_infos+"Samplerate:  %s Hz" % mSamplerate + "\n"
				# file_infos = file_infos+"Length:  %s secs" % mLength + "\n"

				dei = self.session.open(MessageBox, file_infos, MessageBox.TYPE_INFO)
				dei.setTitle("mp3 File Info")

				try:
					ulyrics = ID3(curSelFile).getall('USLT')[0]
					# print('lyrics ->\n%s' % ulyrics)
					dei = self.session.open(MessageBox, str(ulyrics), MessageBox.TYPE_INFO)
					dei.setTitle("mp3 Lyrics")
				except:
					pass
				
				self.file = File(curSelFile)
				try: 
					self.artwork = self.file.tags['APIC:'].data
					with open(cover, 'wb') as img:
						img.write(self.artwork)
					self.picload.getThumbnail(cover)
				except:
					pass
				
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
		if self.isVisible == False:
			self.visibility()
			return
		self.delpath = self.filelist.getFilename()
		if self.delpath is not None:
			delfilename = self.delpath.rsplit("/",1)[1]
			trash = self.delpath
			if '.Trash' in str(trash) and self.filelist.canDescent():
				self.session.openWithCallback(self.emptyTrash, MessageBox, "Empty trash can?\n\n'%s'\n\nAre you shure?" % trash, list=[("No", False), ("Yes", True)])
		self.service = self.filelist.getServiceRef()
		if self.service is None:
			return
		if self.service.type != 4098 and self.session.nav.getCurrentlyPlayingServiceReference() is not None:
			if self.service == self.session.nav.getCurrentlyPlayingServiceReference():
				# self.session.nav.playService(None)
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
			self.session.openWithCallback(self.deleteConfirmed_offline, MessageBox, "This file will be permanently deleted:\n\n'%s'\n\n'%s'\n\nAre you shure?" % (name, delfilename), list=[("No", False), ("Yes", True)])
		else:
			if delfilename.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg', '.mvi', '.webp', '.iso', '.img', '.nrg', '.m3u', '.m3u8', '.tv', '.radio', '.e2pls', '.pls', '.txt')):
				if self.filelist.getSelectionIndex()!=0:
					if delfilename == "":
						pass
					else:
						self.delname = self.delpath
						self.session.openWithCallback(self.deleteFileConfirmed, MessageBox, "This file will be permanently deleted:\n\n'%s'\n\nAre you shure?" % delfilename, list=[("No", False), ("Yes", True)])
				else:
					pass
			else:
				self.session.open(MessageBox, "You cannot delete this!", MessageBox.TYPE_ERROR, close_on_any_key=True)

	def emptyTrash(self, confirmed):
		if confirmed:
			trash = self.delpath
			order = 'rm -f \"' + trash + '\"*' # empty trash can
			# order = 'rm -r \"' + trash + '\"' # delete trash can
			try:
				os_system(order)
			except os_error as oe:
				self.session.open(MessageBox, "Error emptying trash can%s:\n%s" % (trash, oe.strerror), type=MessageBox.TYPE_ERROR, simple=True)
			self.updatelist()

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
				self.session.open(MessageBox, "Delete failed!", MessageBox.TYPE_ERROR)
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
				self.session.open(MessageBox, "non-existent file, could not delete\n\n'%s'" % self.delname, MessageBox.TYPE_WARNING)
			currdir = self.filelist.getCurrentDirectory()
			self.filelist.changeDir(currdir)
			if self.isVisible == False:
				self.visibility()
				return
			self.session.nav.playService(self.oldService)
			self.updatelist()

class m3uOpen(Screen):
	def __init__(self, session, name):
		self.skin = VideoPlayerSimple.skin
		Screen.__init__(self, session)
		
		self.filelist = []
		self["filelist"] = user_list([])
		self.currentList = 'filelist'
		self.hideflag = True
		
		try: fwd15 = lambda: self.seekRelative(1, config.seek.selfdefined_13.value * 90000)
		except: pass
		try: back15 = lambda: self.seekRelative(-1, config.seek.selfdefined_13.value * 90000)
		except: pass
		try: fwd15 = lambda: self.seekRelative(1, config.seek.selfdefined_13.value * 90000)
		except: pass
		try: back60 = lambda: self.seekRelative(-1, config.seek.selfdefined_46.value * 90000)
		except: pass
		try: fwd60 = lambda: self.seekRelative(1, config.seek.selfdefined_46.value * 90000)
		except: pass
		try: back300 = lambda: self.seekRelative(-1, config.seek.selfdefined_79.value * 90000)
		except: pass
		try: fwd300 = lambda: self.seekRelative(1, config.seek.selfdefined_79.value * 90000)
		except: pass
		try: back10 = lambda: self.seekRelative(-1, 10 * 90000)
		except: pass
		try: fwd10 = lambda: self.seekRelative(1, 10 * 90000)
		except: pass

		self['openList'] = ActionMap(['OkCancelActions', 'ColorActions', 'MenuActions', 'NumberActions', 'ChannelSelectBaseActions', 'ChannelSelectEPGActions', 'InfobarTeletextActions'],
		{	# 'red': self.del_entry,
			'1': back15, 
			'3': fwd15,
			'4': back60,
			'6': fwd60,
			'7': back300,
			'9': fwd300,
			'8': self.listbegin,
			'0': self.listend,
			'prevService': back10,
			'nextService': fwd10,
			'menu': self.listtoggle,
			'cancel': self.cancel,
			'startTeletext': self.searchEntry,
			'prevBouquet': self.chDown,
			'nextBouquet': self.chUp,
			'ok': self.okClicked
		}, -2)
        
		self['currentfolder'] = Label('')
		self['currentfolder'].setText('')
		self.name = name
		self.onLayoutFinish.append(self.Openm3u)

	def Openm3u(self):
		from six.moves.urllib.parse import unquote
		from io import open
		self.names = []
		self.urls = []
		content = open(self.name, 'r', encoding='utf-8', errors='ignore').read()
		# content = content.replace('#EXTVLCOPT:http-user-agent=VAVOO/2.6\n', '')
		# # content = re.sub('#EXTVLCOPT:http-user-agent=VAVOO/2.6\n', '', content)
		regexcat = '#EXTINF.*?,(.*?)\\n(.*?)\\n'
		# match = re.compile(regexcat, re.DOTALL).findall(content)
		match = re.compile(regexcat).findall(str(content))
		for name, url in match:
			name = unquote(name)
			url = url.replace(' ', '').replace('\\n', '')
			self.names.append(name)
			self.urls.append(url)
		showlist(self.names, self['filelist'])
		self['currentfolder'].setText(self.name + "  ( " + str(len(self.names)) + ' streams found )')

	def chUp(self):
		for x in range(5):
			self[self.currentList].pageUp()

	def chDown(self):
		for x in range(5):
			self[self.currentList].pageDown()

	def listbegin(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageUp()

	def listend(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageDown()
	
	def listtoggle(self):
		if self.hideflag == True:
			self.hideflag = False
			self.hide()
		else:
			self.hideflag = True
			self.show()
	
	def okClicked(self):
		idx = self['filelist'].getSelectionIndex()
		if idx is None:
			return None
		else:
			name = self.names[idx]
			url = self.urls[idx]
			ref = eServiceReference(4097, 0, url)
			ref.setName(name)
			if config.plugins.videoplayersimple.iptvmovieplayer.value == True:
				self.session.open(MoviePlayer, ref)
			else:
				self.session.nav.playService(ref)
			self["currentfolder"].setText(str(self.name) + " -> " + str(self.names[idx]))
	
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

	def cancel(self):
		Screen.close(self, False)

	def searchEntry(self):
		self.session.openWithCallback(self.filterEntry, VirtualKeyBoard, title="Search for entries in the .m3u(8) list...", text='')

	def filterEntry(self, retval):
		if retval:
			try:
				search = retval
				# print('keyboard input -> %s' % search)
				newList = []
				for file_tuple in self["filelist"].list:
					name = file_tuple
					if search.lower() in str(name).lower():
						newList.append(file_tuple)
				if len(newList) < 1:
					self.session.open(MessageBox, "No entries found!!!", MessageBox.TYPE_INFO, timeout=5)
					return
				else:
					self["filelist"].l.setList(newList)
					self["filelist"].moveToIndex(0)
					self.session.open(MessageBox, "needs to be fixed, search finds entries,\nok plays the first item from the whole\n.m3u(8) list and not from the search list", MessageBox.TYPE_INFO, timeout=6)
					self['currentfolder'].setText(self.name + "  ( " + str(len(newList)) + ' entries found )')
			except Exception as e:
				self.session.open(MessageBox, "Error", MessageBox.TYPE_INFO, timeout=5)
				# print(e)

class e2plsOpen(Screen):
	def __init__(self, session, name):
		self.skin = VideoPlayerSimple.skin
		Screen.__init__(self, session)
		
		self.filelist = []
		self["filelist"] = user_list([])
		self.currentList = 'filelist'
		self.hideflag = True

		self['openList'] = ActionMap(['OkCancelActions', 'ColorActions', 'MenuActions', 'NumberActions', 'ChannelSelectBaseActions'],
		{	# 'red': self.del_entry,
			'8': self.listbegin,
			'0': self.listend,
			'menu': self.listtoggle,
			'cancel': self.cancel,
			'prevBouquet': self.chDown,
			'nextBouquet': self.chUp,
			'ok': self.okClicked
		}, -2)
        
		self['currentfolder'] = Label('')
		self['currentfolder'].setText('')
		self.name = name
		self.onLayoutFinish.append(self.Opene2pls)

	def Opene2pls(self):
		from io import open
		self.names = []
		content = open(self.name, 'r', encoding='utf-8', errors='ignore').read()
		regexcat = '4097\:0\:0\:0\:0\:0\:0\:0\:0\:0\:(.*?)\\n'
		# match = re.compile(regexcat, re.DOTALL).findall(content)
		match = re.compile(regexcat).findall(str(content))
		for name in match:
			self.names.append(name)
		showlist(self.names, self['filelist'])
		self['currentfolder'].setText(self.name + "  ( " + str(len(self.names)) + ' entries found )')

	def chUp(self):
		for x in range(5):
			self[self.currentList].pageUp()

	def chDown(self):
		for x in range(5):
			self[self.currentList].pageDown()

	def listbegin(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageUp()

	def listend(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageDown()

	def listtoggle(self):
		if self.hideflag == True:
			self.hideflag = False
			self.hide()
		else:
			self.hideflag = True
			self.show()

	def okClicked(self):
		idx = self['filelist'].getSelectionIndex()
		if idx is None:
			return None
		else:
			name = self.names[idx]
			ref = eServiceReference(4097, 0, name)
			if config.plugins.videoplayersimple.iptvmovieplayer.value == True:
				self.session.open(MoviePlayer, ref)
			else:
				self.session.nav.playService(ref)
			self["currentfolder"].setText(str(self.name) + " -> " + str(self.names[idx]))

	def cancel(self):
		Screen.close(self, False)

class plsOpen(Screen):
	def __init__(self, session, name):
		self.skin = VideoPlayerSimple.skin
		Screen.__init__(self, session)
		
		self.filelist = []
		self["filelist"] = user_list([])
		self.currentList = 'filelist'
		self.hideflag = True

		self['openList'] = ActionMap(['OkCancelActions', 'ColorActions', 'MenuActions', 'NumberActions', 'ChannelSelectBaseActions'],
		{	# 'red': self.del_entry,
			'8': self.listbegin,
			'0': self.listend,
			'menu': self.listtoggle,
			'cancel': self.cancel,
			'prevBouquet': self.chDown,
			'nextBouquet': self.chUp,
			'ok': self.okClicked
		}, -2)
        
		self['currentfolder'] = Label('')
		self['currentfolder'].setText('')
		self.name = name
		self.onLayoutFinish.append(self.Openpls)

	def Openpls(self):
		from six.moves.urllib.parse import unquote
		from io import open
		self.names = []
		self.urls = []
		content = open(self.name, 'r', encoding='utf-8', errors='ignore').read() # py3 and py2 ok with -> from io import open
		regexcat = 'File.*?=(.*?)\\n.*?=(.*?)\\n'
		# match = re.compile(regexcat,re.DOTALL).findall(content)
		match = re.compile(regexcat).findall(str(content))
		for url, name in match:
			name = unquote(name)
			self.names.append(name)
			self.urls.append(url)
		showlist(self.names, self["filelist"])
		self['currentfolder'].setText(self.name + "  ( " + str(len(self.names)) + ' streams found )')

	def chUp(self):
		for x in range(5):
			self[self.currentList].pageUp()

	def chDown(self):
		for x in range(5):
			self[self.currentList].pageDown()

	def listbegin(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageUp()

	def listend(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageDown()

	def listtoggle(self):
		if self.hideflag == True:
			self.hideflag = False
			self.hide()
		else:
			self.hideflag = True
			self.show()

	def okClicked(self):
		idx = self['filelist'].getSelectionIndex()
		if idx is None:
			return None
		else:
			name = self.names[idx]
			url = self.urls[idx]
			ref = eServiceReference(4097, 0, url)
			ref.setName(name)
			if config.plugins.videoplayersimple.iptvmovieplayer.value == True:
				self.session.open(MoviePlayer, ref)
			else:
				self.session.nav.playService(ref)
			self["currentfolder"].setText(str(self.name) + " -> " + str(self.names[idx]))
			
	def cancel(self):
		Screen.close(self, False)

class txtOpen(Screen):
	def __init__(self, session, name):
		self.skin = VideoPlayerSimple.skin
		Screen.__init__(self, session)
		
		self.filelist = []
		self["filelist"] = user_list([])
		self.currentList = 'filelist'
		self.hideflag = True

		self['openList'] = ActionMap(['OkCancelActions', 'ColorActions', 'MenuActions', 'NumberActions', 'ChannelSelectBaseActions', 'InfobarTeletextActions'],
		{	# 'red': self.del_entry,
			'8': self.listbegin,
			'0': self.listend,
			'menu': self.listtoggle,
			'cancel': self.cancel,
			'prevBouquet': self.chDown,
			'nextBouquet': self.chUp,
			'startTeletext': self.showLine,
			'ok': self.okClicked
		}, -2)
        
		self['currentfolder'] = Label('')
		self['currentfolder'].setText('')
		self.name = name
		self.onLayoutFinish.append(self.Opentxt)

	def Opentxt(self):
		from six.moves.urllib.parse import unquote
		from io import open
		self.names = []
		content = open(self.name, 'r', encoding='utf-8', errors='ignore').read() # py3 and py2 ok with -> from io import open
		regexcat = '(.*?)\\n'
		match = re.compile(regexcat).findall(str(content))
		for name in match:
			name = unquote(name)
			self.names.append(name)
		showlist(self.names, self["filelist"])
		self['currentfolder'].setText(self.name + "  ( " + str(len(self.names)) + ' streams / lines found )')
			
	def chUp(self):
		for x in range(5):
			self[self.currentList].pageUp()

	def chDown(self):
		for x in range(5):
			self[self.currentList].pageDown()

	def listbegin(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageUp()

	def listend(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageDown()

	def listtoggle(self):
		if self.hideflag == True:
			self.hideflag = False
			self.hide()
		else:
			self.hideflag = True
			self.show()

	def showLine(self):
		idx = self['filelist'].getSelectionIndex()
		if idx is None:
			return None
		else:
			self.viewLine = self.names[idx]
		self.session.open(MessageBox, "%s" % self.viewLine, MessageBox.TYPE_MESSAGE, simple=True)
		
	def okClicked(self):
		idx = self['filelist'].getSelectionIndex()
		if idx is None:
			return None
		else:
			name = self.names[idx]
			ref = eServiceReference(4097, 0, name)
			# ref.setName(name)
			if config.plugins.videoplayersimple.iptvmovieplayer.value == True:
				self.session.open(MoviePlayer, ref)
			else:
				self.session.nav.playService(ref)
			self["currentfolder"].setText(str(self.name) + " -> " + str(self.names[idx]))

	def cancel(self):
		Screen.close(self, False)

class userbouquetTvOpen(Screen):
	def __init__(self, session, name):
		self.skin = VideoPlayerSimple.skin
		Screen.__init__(self, session)
		
		self.filelist = []
		self["filelist"] = user_list([])
		self.currentList = 'filelist'
		self.hideflag = True

		try: fwd15 = lambda: self.seekRelative(1, config.seek.selfdefined_13.value * 90000)
		except: pass
		try: back15 = lambda: self.seekRelative(-1, config.seek.selfdefined_13.value * 90000)
		except: pass
		try: fwd15 = lambda: self.seekRelative(1, config.seek.selfdefined_13.value * 90000)
		except: pass
		try: back60 = lambda: self.seekRelative(-1, config.seek.selfdefined_46.value * 90000)
		except: pass
		try: fwd60 = lambda: self.seekRelative(1, config.seek.selfdefined_46.value * 90000)
		except: pass
		try: back300 = lambda: self.seekRelative(-1, config.seek.selfdefined_79.value * 90000)
		except: pass
		try: fwd300 = lambda: self.seekRelative(1, config.seek.selfdefined_79.value * 90000)
		except: pass
		try: back10 = lambda: self.seekRelative(-1, 10 * 90000)
		except: pass
		try: fwd10 = lambda: self.seekRelative(1, 10 * 90000)
		except: pass

		self['openList'] = ActionMap(['OkCancelActions', 'ColorActions', 'MenuActions', 'NumberActions', 'ChannelSelectBaseActions', 'ChannelSelectEPGActions', 'InfobarTeletextActions'],
		{	# 'red': self.del_entry,
			'1': back15, 
			'3': fwd15,
			'4': back60,
			'6': fwd60,
			'7': back300,
			'9': fwd300,
			'8': self.listbegin,
			'0': self.listend,
			'prevService': back10,
			'nextService': fwd10,
			'menu': self.listtoggle,
			'cancel': self.cancel,
			'startTeletext': self.searchEntry,
			'prevBouquet': self.chDown,
			'nextBouquet': self.chUp,
			'ok': self.okClicked
		}, -2)
        
		self['currentfolder'] = Label('')
		self['currentfolder'].setText('')
		self.name = name
		self.onLayoutFinish.append(self.openUserbouquet)

	def openUserbouquet(self):
		from six.moves.urllib.parse import unquote
		from io import open
		self.names = []
		self.urls = []
		content = open(self.name, 'r', encoding='utf-8', errors='ignore').read() # py3 and py2 ok with -> from io import open
		# content = open(self.name, 'r').read().decode('UTF-8') #only py2
		if config.plugins.videoplayersimple.iptvdescription.value == True:
			regexcat = '#SERVICE [^hmrSsYy]+(.*?)\:(.*?)\\n' # from the first occurance of "(h)ttp", "(m)ms", "(r)tm(p)", "rtp(s)", "(Ss)treamlink", "(Yy)T-DL(P)" and before last occurance of ":", phew!, took me hours
		else:
			regexcat = '#SERVICE [^hmrSsYy]+(.*?)\\n#DESCRIPTION (.*?)\\n' # takes description from second line and not after ":", HDF .radio list ok
		# match = re.compile(regexcat,re.DOTALL).findall(content)
		match = re.compile(regexcat).findall(str(content))
		for url, name in match:
			# name = name.replace("%20", " ").replace("%", "_")
			name = unquote(name)
			if config.plugins.videoplayersimple.iptvdescription.value == False:
				url = url.split(':', 1)[0] # ok
			url = url.replace("%3a", ":").replace("%3A", ":")
			self.names.append(name)
			self.urls.append(url)
		showlist(self.names, self["filelist"])
		self['currentfolder'].setText(self.name + "  ( " + str(len(self.names)) + ' streams found )')

	def chUp(self):
		for x in range(5):
			self[self.currentList].pageUp()

	def chDown(self):
		for x in range(5):
			self[self.currentList].pageDown()

	def listbegin(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageUp()

	def listend(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageDown()

	def listtoggle(self):
		if self.hideflag == True:
			self.hideflag = False
			self.hide()
		else:
			self.hideflag = True
			self.show()
	
	def okClicked(self):
		idx = self['filelist'].getSelectionIndex()
		if idx is None:
			return None
		else:
			name = self.names[idx]
			url = self.urls[idx]
			ref = eServiceReference(4097, 0, url)
			ref.setName(name)
			if config.plugins.videoplayersimple.iptvmovieplayer.value == True:
				self.session.open(MoviePlayer, ref)
			else:
				self.session.nav.playService(ref)
			self["currentfolder"].setText(str(self.name) + " -> " + str(self.names[idx]))

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
			
	def cancel(self):
		Screen.close(self, False)

	def searchEntry(self):
		self.session.openWithCallback(self.filterEntry, VirtualKeyBoard, title="Search for entries in the .tv list...", text='')

	def filterEntry(self, retval):
		if retval:
			try:
				search = retval
				# print('keyboard input -> %s' % search)
				newList = []
				for file_tuple in self["filelist"].list:
					name = file_tuple
					if search.lower() in str(name).lower():
						newList.append(file_tuple)
				if len(newList) < 1:
					self.session.open(MessageBox, "No entries found!!!", MessageBox.TYPE_INFO, timeout=5)
					return
				else:
					self["filelist"].l.setList(newList)
					self["filelist"].moveToIndex(0)
					self.session.open(MessageBox, "needs to be fixed, search finds entries,\nok plays the first item from the whole\n.tv list and not from the search list", MessageBox.TYPE_INFO, timeout=6)
					self['currentfolder'].setText(self.name + "  ( " + str(len(newList)) + ' entries found )')
			except Exception as e:
				self.session.open(MessageBox, "Error", MessageBox.TYPE_INFO, timeout=5)
				# print(e)

class userbouquetRadioOpen(Screen):
	def __init__(self, session, name):
		self.skin = VideoPlayerSimple.skin
		Screen.__init__(self, session)
		
		self.filelist = []
		self["filelist"] = user_list([])
		self.currentList = 'filelist'
		self.hideflag = True
				
		self['openList'] = ActionMap(['OkCancelActions', 'ColorActions', 'MenuActions', 'NumberActions', 'ChannelSelectBaseActions', 'ChannelSelectEPGActions', 'InfobarTeletextActions'],
		{	# 'red': self.del_entry,
			'8': self.listbegin,
			'0': self.listend,
			'7': self.showStreamTitle,
			'9': self.okClicked,
			'menu': self.listtoggle,
			'cancel': self.cancel,
			'prevBouquet': self.chDown,
			'nextBouquet': self.chUp,
			'startTeletext': self.searchEntry,
			'prevMarker': self.prevStreamTitle,
			'nextMarker': self.nextStreamTitle,
			'ok': self.okClicked
		}, -2)
		
		self['currentfolder'] = Label('')
		self['currentfolder'].setText('')
		self.name = name
		self.onLayoutFinish.append(self.openUserbouquet)

	def openUserbouquet(self):
		from six.moves.urllib.parse import unquote
		from io import open
		self.names = []
		self.urls = []
		content = open(self.name, 'r', encoding='utf-8', errors='ignore').read() # py3 and py2 ok with -> from io import open
		# content = open(self.name, 'r').read().decode('UTF-8') # only py2
		if config.plugins.videoplayersimple.iptvdescription.value == True:
			regexcat = '#SERVICE [^hmrSsYy]+(.*?)\:(.*?)\\n' # from the first occurance of "(h)ttp", "(m)ms", "(r)tm(p)", "rtp(s)", "(Ss)treamlink", "(Yy)T-DL(P)" and before last occurance of ":", phew!, took me hours
		else:
			regexcat = '#SERVICE [^hmrSsYy]+(.*?)\\n#DESCRIPTION (.*?)\\n' # takes description from second line and not after ":", HDF .radio list ok
		# match = re.compile(regexcat,re.DOTALL).findall(content)
		match = re.compile(regexcat).findall(str(content))
		for url, name in match:
			# name = name.replace("%20", " ").replace("%", "_")
			name = unquote(name)
			if config.plugins.videoplayersimple.iptvdescription.value == False:
				url = url.split(':', 1)[0] # ok
			url = url.replace("%3a", ":").replace("%3A", ":")
			self.names.append(name)
			self.urls.append(url)
		showlist(self.names, self["filelist"])
		self['currentfolder'].setText(self.name + '  ( ' + str(len(self.names)) + ' streams found )')

	def prevStreamTitle(self):
		self[self.currentList].up()
		self.showStreamTitle()

	def nextStreamTitle(self):
		self[self.currentList].down()
		self.showStreamTitle()

	def chUp(self):
		for x in range(5):
			self[self.currentList].pageUp()

	def chDown(self):
		for x in range(5):
			self[self.currentList].pageDown()

	def listbegin(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageUp()

	def listend(self):
		indx = len(self.names)
		for x in range(indx):
			self[self.currentList].pageDown()

	def listtoggle(self):
		if self.hideflag == True:
			self.hideflag = False
			self.hide()
		else:
			self.hideflag = True
			self.show()

	def showStreamTitle(self):
		try:
			import requests
		except ImportError:
			self.session.open(MessageBox, "install requests package !\nopkg install python-requests\nor\nopkg install python3-requests", MessageBox.TYPE_INFO, timeout=5)
			print(("\ninstall requests package, 'opkg install python-requests' or 'opkg install python3-requests'\n"))
		
		idx = self['filelist'].getSelectionIndex()
		if idx is None:
			return None
		else:
			name = self.names[idx]
			url = self.urls[idx]
			try:
				response = requests.get(url, headers={'Icy-MetaData': '1'}, stream=True, timeout=10, verify=None)
				response.raise_for_status()
				headers, stream = response.headers, response.raw
				meta_int = headers.get('icy-metaint')
				if meta_int is not None:
				        audio_length = int(meta_int)
				audio_data = stream.read(audio_length)
				meta_byte = stream.read(1)
				if (meta_byte):
					meta_length = ord(meta_byte) * 16
					meta_data = stream.read(meta_length)
					meta_data = meta_data.split(b"StreamTitle='")[1].split(b"';")[0].decode("utf-8", errors="replace")
					# print ("%s" % name)
					# print ("ICY title -> %s" % str(meta_data))
					# self["currentfolder"].setText("" + "\n\n" + str(meta_data))
					self["currentfolder"].setText(str(name) + " -> " + str(meta_data))
			
			except requests.ConnectionError as e:
				# print("[ICY title] -> Connection Error\n")
				self["currentfolder"].setText("Connection Error: -> " + str(name) + " -> " + str(e))
				requests.session().close()
			except requests.Timeout as e:
				# print("[ICY title] -> Timeout Error\n")
				self["currentfolder"].setText("Timeout Error: -> " + str(name) + " -> " + str(e))
				requests.session().close()
			except requests.RequestException as e:
				# print("[ICY title] -> General Error\n")
				self["currentfolder"].setText("General Error: -> " + str(name) + " -> " + str(e))
				requests.session().close()
			except:
				# print ("Error or icy metadata not available")
				self["currentfolder"].setText(str(name) + " -> " + "Error or icy metadata not available")
	
	def okClicked(self):
		idx = self['filelist'].getSelectionIndex()
		if idx is None:
			return None
		else:
			name = self.names[idx]
			url = self.urls[idx]
			ref = eServiceReference(4097, 0, url)
			ref.setName(name)
			if config.plugins.videoplayersimple.iptvmovieplayer.value == True:
				self.session.open(MoviePlayer, ref)
			else:
				self.session.nav.playService(ref)
			self["currentfolder"].setText(str(self.name) + " -> " + str(self.names[idx]))

	def cancel(self):
		Screen.close(self, False)

	def searchEntry(self):
		self.session.openWithCallback(self.filterEntry, VirtualKeyBoard, title="Search for entries in the .radio list...", text='')

	def filterEntry(self, retval):
		if retval:
			try:
				search = retval
				# print('keyboard input -> %s' % search)
				newList = []
				for file_tuple in self["filelist"].list:
					name = file_tuple
					if search.lower() in str(name).lower():
						newList.append(file_tuple)
				if len(newList) < 1:
					self.session.open(MessageBox, "No entries found!!!", MessageBox.TYPE_INFO, timeout=5)
					return
				else:
					self["filelist"].l.setList(newList)
					self["filelist"].moveToIndex(0)
					self.session.open(MessageBox, "needs to be fixed, search finds entries,\nok plays the first item from the whole\n.radio list and not from the search list", MessageBox.TYPE_INFO, timeout=6)
					self['currentfolder'].setText(self.name + "  ( " + str(len(newList)) + ' entries found )')
			except Exception as e:
				self.session.open(MessageBox, "Error", MessageBox.TYPE_INFO, timeout=5)
				# print(e)
	
class user_list(MenuList):
	def __init__(self, list):
		MenuList.__init__(self, list, True, eListboxPythonMultiContent)
		if (getDesktop(0).size().width() >= 1920):
			self.l.setItemHeight(44)
			textfont = int(30)
			self.l.setFont(0, gFont('Regular', textfont))
		else:
			self.l.setItemHeight(30)
			textfont = int(20)
			self.l.setFont(0, gFont('Regular', textfont))

def showlist(data, list):
	icount = 0
	mlist = []
	for line in data:
		name = data[icount]
		mlist.append(user_show(name))
		icount += 1
	list.setList(mlist)

def user_show(name):
	res = [name]
	if (getDesktop(0).size().width() >= 1920):
		res.append(MultiContentEntryText(pos=(12, 4), size=(1880, 44), text=name))
	else:
		res.append(MultiContentEntryText(pos=(8, 2), size=(1250, 30), text=name))
	return res

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
		Screen.__init__(self, session)
		self.session = session
		self.whatPic = whatPic
		self.whatDir = whatDir
		self.picList = []
		self.Pindex = 0
		# self.EXscale = (AVSwitch().getFramebufferScale())
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
			# self.EXpicload.setPara([self["Picture"].instance.size().width(), self["Picture"].instance.size().height(), self.EXscale[0], self.EXscale[1], 0, 1, "#FF2C2C39", 1])
			self.EXpicload.setPara([self["Picture"].instance.size().width(), self["Picture"].instance.size().height(), 1, 1, 0, 1, "#FF2C2C39", 1])
			self.EXpicload.startDecode(self.whatPic)
		if self.whatDir is not None:
			pidx = 0
			for (root, dirs, files) in os_walk(self.whatDir):
				for name in sorted(files, key=str.lower):				
					if name.lower().endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.bmp', '.svg')):
						self.picList.append(name)
						if name in self.whatPic:
							self.Pindex = pidx
						pidx += 1
				break # only current dir without subdirs

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
				self.Pleft()

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
				self.Pright()				
	
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
