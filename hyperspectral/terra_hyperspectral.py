#!/usr/bin/env python

import os
import subprocess
import json
import logging
import tempfile
from netCDF4 import Dataset

from pyclowder.utils import CheckMessage
from pyclowder.datasets import download_metadata
from pyclowder.files import upload_to_dataset
from terrautils.metadata import get_extractor_metadata, get_terraref_metadata
from terrautils.extractors import TerrarefExtractor, is_latest_file, build_dataset_hierarchy
from terrautils.betydb import submit_traits, add_arguments


def add_local_arguments(parser):
	# add any additional arguments to parser
	# self.parser.add_argument('--max', '-m', type=int, nargs='?', default=-1,
	#                          help='maximum number (default=-1)')
	add_arguments(parser)

class HyperspectralRaw2NetCDF(TerrarefExtractor):
	def __init__(self):
		super(HyperspectralRaw2NetCDF, self).__init__()

		add_local_arguments(self.parser)

		# parse command line and load default logging configuration
		self.setup(sensor='vnir_netcdf')

		# assign other argumentse
		self.bety_url = self.args.bety_url
		self.bety_key = self.args.bety_key

	def check_message(self, connector, host, secret_key, resource, parameters):
		#if not is_latest_file(resource):
		#	return CheckMessage.ignore

		# Adjust sensor path based on VNIR vs SWIR
		if resource['dataset_info']['name'].find("SWIR") > -1:
			sensor_fullname = 'swir_netcdf'
		else:
			sensor_fullname = 'vnir_netcdf'

		if has_all_files(resource):
			# Check if output already exists
			timestamp = resource['dataset_info']['name'].split(" - ")[1]
			outFilePath = self.sensors.get_sensor_path(timestamp, sensor=sensor_fullname)

			if os.path.exists(outFilePath) and not self.overwrite:
				self.log_skip(resource, 'output file already exists')
				return CheckMessage.ignore
			else:
				# Check if we have necessary metadata, either as a .json file or attached to dataset
				md = download_metadata(connector, host, secret_key, resource['id'], self.extractor_info['name'])
				if get_extractor_metadata(md, self.extractor_info['name']) and not self.overwrite:
					self.log_skip(resource, "already processed")
					return CheckMessage.ignore
				else:
					return CheckMessage.download
				""" TODO: Re-enable this logic after metadata is cleaned
				elif get_terraref_metadata(md):
					return CheckMessage.download
				else:
					for f in resource['files']:
						if f['filename'] == 'metadata.json':
							return CheckMessage.download
					return CheckMessage.ignore
				"""
		else:
			self.log_skip(resource, 'not all input files are ready')
			return CheckMessage.ignore

	def process_message(self, connector, host, secret_key, resource, parameters):
		self.start_message(resource)

		# Find input files in dataset
		target_files = {
			'raw': None,
			'raw.hdr': None,
			'image.jpg': None,
			'frameIndex.txt': None,
			'settings.txt': None,
			"_metadata.json": None
		}

		metafile = None
		ds_metafile = None
		last_path = None
		path_match = None
		tempdir = None
		symlinks = []
		for f in resource['local_paths']:
			for fileExt in target_files.keys():
				if f.endswith(fileExt):
					if fileExt != '_metadata.json':
						filedir = os.path.dirname(f)
						if not last_path:
							last_path = filedir
						else:
							if filedir != last_path:
								path_match = False
							last_path = filedir
						target_files[fileExt] = {'filename': os.path.basename(f), 'path': f}
					else:
						if f.endswith('/_dataset_metadata.json'):
							ds_metafile = f
						elif not f.endswith('/_metadata.json'):
							metafile = f
							target_files['_metadata.json'] = {'filename': os.path.basename(metafile),
															  'path': metafile}

		# Identify md file either with other dataset files, or attached to Clowder dataset
		if metafile == None:
			if ds_metafile != None:
				# Found dataset metadata, so check for the .json file alongside other files
				self.log_info(resource, "checking for local metadata file alongside other files")
				ds_dir = os.path.dirname(target_files['raw']['path'])
				for ds_f in os.path.listdir(ds_dir):
					if ds_f.endswith("_metadata.json"):
						target_files['_metadata.json']['path'] = os.path.join(ds_dir, ds_f)
			else:
				raise ValueError('could not locate metadata for %s' % resource['id'])

		# Create symlinks in one directory if inputs aren't in the same one
		if not path_match:
			tempdir = tempfile.mkdtemp()
			for f in target_files.keys():
				currf = target_files[f]
				if currf['filename'] == '_dataset_metadata.json':
					# Open the temporary file and change the JSON content format
					with open(currf['path'], 'r') as mdfile:
						jsondata = json.load(mdfile)
					md = get_terraref_metadata(jsondata)
					with open(currf['path'], 'w') as mdfile:
						json.dump(md, mdfile)
					newf = os.path.join(tempdir, target_files['raw']['filename'].replace("_raw","")+'_metadata.json')
				else:
					newf = os.path.join(tempdir, currf['filename'])
				os.symlink(currf['path'], newf)
				symlinks.append(newf)


		# Adjust sensor path based on VNIR vs SWIR and check for soil mask
		timestamp = resource['dataset_info']['name'].split(" - ")[1]
		if resource['dataset_info']['name'].find("SWIR") > -1:
			sensor_fullname = 'swir_netcdf'
			soil_mask = None
		else:
			sensor_fullname = 'vnir_netcdf'
			# Check for corresponding soil mask to include in workflow.sh if available
			soil_mask = self.sensors.get_sensor_path(timestamp, sensor='vnir_soil_masks', opts=['soil_mask'])
		outFilePath = self.sensors.create_sensor_path(timestamp, sensor=sensor_fullname)

		# Invoke terraref.sh
		self.log_info(resource, 'invoking hyperspectral_workflow.sh to create: %s' % outFilePath)
		if soil_mask:
			returncode = subprocess.call(["bash", "hyperspectral_workflow.sh", "-d", "1", "-h",
										  "-m", soil_mask, "--new_clb_mth",
										  "-i", target_files['raw']['path'], "-o", outFilePath])
		else:
			returncode = subprocess.call(["bash", "hyperspectral_workflow.sh", "-d", "1", "-h",
										 "--new_clb_mth",
										 "-i", target_files['raw']['path'], "-o", outFilePath])

		# Verify outfile exists and upload to clowder
		self.log_info(resource, 'done creating output file (%s)' % (returncode))
		if returncode != 0:
			raise ValueError('script encountered an error')
		if os.path.exists(outFilePath):
			if returncode == 0:
				if outFilePath not in resource['local_paths']:
					target_dsid = build_dataset_hierarchy(host, secret_key, self.clowder_user, self.clowder_pass, self.clowderspace,
														  self.sensors.get_display_name(sensor=sensor_fullname),
														  timestamp[:4], timestamp[5:7], timestamp[8:10],
														  leaf_ds_name=self.sensors.get_display_name(sensor=sensor_fullname)+' - '+timestamp)

					self.log_info(resource, 'uploading %s' % outFilePath)
					upload_to_dataset(connector, host, secret_key, target_dsid, outFilePath)
				self.created += 1
				self.bytes += os.path.getsize(outFilePath)
		else:
			self.log_error(resource, 'no output file was produced')

		# Send indices to betyDB
		ind_file = self.sensors.get_sensor_path(timestamp, sensor=sensor_fullname, opts=['_ind'])
		with Dataset(ind_file, "r") as netCDF_handle:
			ndvi = netCDF_handle.get_variables_by_attributes(
					standard_name='normalized_difference_chlorophyll_index_750_705')
			NDVI705 = ndvi[0].getValue().ravel()[0]

			# TODO: Create CSV using ndviVal as primary key
			tmp_csv = 'traits.csv'
			plot_no = 'Full Field'
			csv_header = 'local_datetime,NDVI705,access_level,species,site,' \
						 'citation_author,citation_year,citation_title,method'
			csv_vals = '%s,%s,2,Sorghum bicolor,%s,"Butowsky, Henry",2016,' \
					   'Maricopa Field Station Data and Metadata,Hyperspectral NDVI705 Indices' % (
							timestamp, NDVI705, plot_no)
			with open(tmp_csv, 'w') as c:
				c.write(csv_header+'\n'+csv_vals)

		submit_traits(tmp_csv, bety_key=self.bety_key)

		# Remove symlinks and temp directory
		for sym in symlinks:
			os.remove(sym)
		if tempdir:
			os.rmdir(tempdir)

		self.end_message(resource)

# Find as many expected files as possible and return the set.
def get_all_files(resource):
	target_files = {
		'raw': None,
		'raw.hdr': None,
		'image.jpg': None,
		'frameIndex.txt': None,
		'settings.txt': None
	}

	if 'files' in resource:
		for fileItem in resource['files']:
			fileId   = fileItem['id']
			fileName = fileItem['filename']
			for fileExt in target_files.keys():
				if fileName.endswith(fileExt):
					target_files[fileExt] = {
						'id': fileId,
						'filename': fileName
					}

	return target_files

# Returns true if all expected files are found.
def has_all_files(resource):
	target_files = get_all_files(resource)

	allFilesFound = True
	for fileExt in target_files:
		if target_files[fileExt] == None:
			allFilesFound = False

	return allFilesFound

def _produce_attr_dict(netCDF_variable_obj):
	'''Produce a list of dictionary with attributes and value'''
	attributes = [attr for attr in dir(netCDF_variable_obj) if isinstance(attr, unicode)]
	result     = {name:getattr(netCDF_variable_obj, name) for name in attributes}

	return [dict(result.items()+ {"value":str(data)}.items()) for data in netCDF_variable_obj[...]]

if __name__ == "__main__":
	extractor = HyperspectralRaw2NetCDF()
	extractor.start()
