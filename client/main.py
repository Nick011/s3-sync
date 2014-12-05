import os
import sys
import time
import logging
import boto
import json
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
from pprint import pprint
from boto.s3.key import Key
from socketIO_client import SocketIO
import threading
import wx


#move to env variables or settings file
AWS_KEY = ""
AWS_SECRET = ""
S3_BUCKET = ""
ROOT_FOLDER_NAME = "/demo/"

#watchdog
class FolderEvent(FileSystemEventHandler):
	#def __init__(self, *args, **kwargs):
		#FileSystemEventHandler.__init__(self)

	#def dispatch_event(self, *args, **kwargs):
		#s3.__getattr__('_'.join([kwargs['ename'], kwargs['type']]))

	#def on_any_event(self, event):
		#print "e=", event
		#pprint (vars(event))

	def build_req(self, event):
		return {'is_directory':event.is_directory, 'path': event.src_path.split(ROOT_FOLDER_NAME)[1]}

	def on_created(self, event):
		if event.is_directory:
			s3.create_folder(event.src_path)
		else:
			s3.create_file(event.src_path)

		#local_sync.pub_create(self.build_req(event))

	def on_deleted(self, event):
		if event.is_directory:
			s3.delete_folder(event.src_path)
		else:
			s3.delete_file(event.src_path)
		#local_sync.pub_delete(self.build_req(event))

	def on_moved(self, event):
		#if event.is_directory:
			#s3.move_dir(from=event.src_path, to=event.dest_path)
		#	return True
		#else:
		s3.create_file(event.dest_path)
		s3.delete_file(event.src_path)

	def on_modified(self, event):
		if not event.is_directory:
			s3.create_file(event.src_path)
			#local_sync.pub_delete(self.build_req(event))
			#local_sync.pub_create(self.build_req(event))



class S3:
	def __init__(self, *args, **kwargs):
		conn = boto.connect_s3(AWS_KEY, AWS_SECRET)
		self.bucket = conn.get_bucket(S3_BUCKET)
	
	def aws_path(self, path):
		return path.split(ROOT_FOLDER_NAME)[1]

	def write_structure(self, key):
		#create the file/folder if it's not there
		local_path = '/'.join([self.local_root + key.name])
		local_dir = os.path.dirname(local_path)
		if not os.path.exists(local_dir):
			os.makedirs(local_dir)

		if not key.name.endswith('/'):
			with open(local_path, 'w') as f:
				f.write(key.get_contents_as_string())

	def fetch_all(self, local_root):
		self.local_root = local_root
		for key in self.bucket.list():
			self.write_structure(key)

	def fetch_key(self, key_name):
		k = self.bucket.get_key(key_name)
		if not k: return None
		self.write_structure(key)

	def create_folder(self, path):
		path += '/.demo'
		k = Key(self.bucket)
		k.key = self.aws_path(path)
		k.set_contents_from_string(' ')

	def create_file(self, path):
		k = Key(self.bucket)
		k.key = self.aws_path(path)
		k.set_contents_from_file(file(path, 'r'))

	def delete_folder(self, path):
		prefix = self.aws_path(path)
		[k.delete() for k in self.bucket.list(prefix)]

	def delete_file(self, path):
		key_name = self.aws_path(path)
		k = self.bucket.get_key(key_name)
		if k: k.delete()


class LocalSync:
	prop_blacklist = []
	def __init__(self, *args, **kwargs):
		self.socket = SocketIO('localhost', 8000)
		t = threading.Thread(target=self.listener)
		t.start()

	def listener(self):
		self.socket.on('create', self.sub_create)
		self.socket.on('delete', self.sub_delete)
		self.socket.wait()

	def should_propagate(self, path):
		if path in self.prop_blacklist:
			self.prop_blacklist.remove(path)
			return False
		return True

	def sub_create(self, *args):
		print 'create called'
		pprint(args)
		event = json.loads(args[0])
		self.prop_blacklist.append(event.path)
		s3.fetch_key(event.path)

	def sub_delete(self, *args):
		print 'delete called'
		event = json.loads(args[0])
		self.prop_blacklist.append(event.path)
		os.remove('/'.join([s3.local_root, event.path]))

	def pub_create(self, req):
		if self.should_propagate(req.path):
			self.socket.emit('create', json)

	def pub_delete(self, req):
		if self.should_propagate(req.path):
			self.socket.emit('delete', json.dumps(req))



########################################################################
class MyForm(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, wx.ID_ANY,
			"File and Folder Dialogs Tutorial")
		panel = wx.Panel(self, wx.ID_ANY)
		self.currentDirectory = os.getcwd()

		dirDlgBtn = wx.Button(panel, label="Show DirDialog")
		dirDlgBtn.Bind(wx.EVT_BUTTON, self.onDir)

	#----------------------------------------------------------------------
	def onDir(self, event):
		"""
		Show the DirDialog and print the user's choice to stdout
		"""
		dlg = wx.DirDialog(self, "Choose a directory:",
												style=wx.DD_DEFAULT_STYLE
	                       #| wx.DD_DIR_MUST_EXIST
	                       #| wx.DD_CHANGE_DIR
	                       )

		if dlg.ShowModal() == wx.ID_OK:
			self.demo_folder = dlg.GetPath() + ROOT_FOLDER_NAME
			self.set_observer()
			s3.fetch_all(self.demo_folder)
	
	#---		
	def set_observer(self):
		if not os.path.exists(self.demo_folder): os.makedirs(self.demo_folder)

		event_handler = FolderEvent()
		observer = Observer()
		observer.schedule(event_handler, self.demo_folder, recursive=True)
		observer.start()



#----------------------------------------------------------------------
# Run the program
if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO,
	format='%(asctime)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S')

	#connect s3
	s3 = S3()
	#local_sync = LocalSync()
	app = wx.App(False)
	frame = MyForm()
	frame.Show()
	app.MainLoop()

