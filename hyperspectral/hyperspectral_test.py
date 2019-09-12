#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
import unittest
import argparse
import sys
from netCDF4 import Dataset

'''
Test for Hyperspectral Workflow

This script does not check whether all the data are correct (because there are too many of them),
instead, it will check whether it has enough number of groups, dimensions, and variables,
and will take one or two samples to check the values.

==============================================================================
To run the test from the commandline, do:
python hyperspectral_test.py <input_netCDF_file> <verbosity_level> <maximum_plant_reflectance>

* verbosity level can be 0, 1 or 2 (from the quietest to the most verbose)

==============================================================================
It will check the followings so far:
1. Have enough number of root level groups
2. Have enough number of root level dimensions
3. Have enough number of root level variables
4. The dimensions are all correct (in both name and numerical value)
5. The groups are all correctly named
6. The wavelengths are correctly written (in both name and numerical value)
7. The georeferencing data are correctly recorded
8. The RGB indices are correctly recorded (in both name and numerical value)
9. The history is correctly recorded (match the regex pattern)
10. Check the variables are saved in proper data types

==============================================================================
NOTES:
* 1. This test module now have an exit code. Usually it is used to be trapped by 
*    Hyperspectral master script.
* 2. Feel free to add more testcases! Follow this format:
*    -----------------------------------------------------------------------------------
*    def <the_name_of_this_testcase_starts_with_"test">(self):
*        self.<data> = blahblahblah... //How do you retrieve this data from the dataset
*        self.assertEqual(self.<data>, <expected_value>, msg=<your_message>)
*    -----------------------------------------------------------------------------------
* 3. Add @unittest.expectedFailure for those test which results has not been implemented
*
*
'''

EXPECTED_NUMBER_OF_GROUPS     = 6
EXPECTED_NUMBER_OF_DIMENSIONS = 4
TEST_FILE_DIRECTORY           = None
MAXIMUM_PLANT_REFLECTANCE     = 0.6
DEFAULT_SATURATED_EXPOSURE    = 2**16 - 1



class HyperspectralWorkflowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        '''
        Set up the environment before all the test cases are triggered
        '''
        cls.masterNetCDFHandler = Dataset(TEST_FILE_DIRECTORY, "r")
        cls.groups     = cls.masterNetCDFHandler.groups
        cls.dimensions = cls.masterNetCDFHandler.dimensions
        cls.flatten = True if len(cls.groups) > 1 else False

    @classmethod
    def tearDownClass(cls):
        '''Do the clean up after all the test cases were finished'''
        cls.masterNetCDFHandler.close()

    def assertHasAttribute(self, object, attr, msg=None):
        '''Home-made attribute test method'''
        if not hasattr(object, attr):

            msg = self._formatMessage(msg, "%s has no attribute %s"%(unittest.util.safe_repr(object), attr))
            raise self.failureException(msg)

    #################### Test Cases ####################

    # def testTheNumberOfGroupsInRootLevelIsCorrect(self):
    #     '''
    #     Check if there are six groups in the root level
    #     '''
    #     self.assertEqual(len(self.groups), EXPECTED_NUMBER_OF_GROUPS, msg="There should be six groups total")

    @unittest.expectedFailure
    def testTheNumberOfDimensionsInRootLevelIsCorrect(self):
        '''
        Check if there are four dimensions in the root level
        '''
        self.assertEqual(len(self.dimensions), EXPECTED_NUMBER_OF_DIMENSIONS, msg="There should be four dimensions total")

    # def testTheXDimensionsHaveCorrectValues(self):
    #     self.assertEqual(len(self.dimensions["x"]),    1600, msg="The dimension for x should be 1600")

    def testTheYDimensionsMatchesTimeDimension(self):
        self.assertEqual(len(self.dimensions["y"]), len(self.dimensions["time"]),  msg="The dimension for y should be the same as for time")

    def testTheWavelengthDimensionsHaveCorrectValues(self):
        self.assertIn(len(self.dimensions["wavelength"]), (272, 273, 275, 939, 955), msg="The dimension for wavelength is wrong")

    # def testTheGantrySystemFixedMetadataGroupIsCorrectlyNamed(self):
    #     '''
    #     Check if all the groups are named as what we want
    #     '''
    #     self.assertIn("gantry_system_fixed_metadata", self.groups, msg="gantry_system_fixed_metadata should be a group in root level")
        
    # def testTheSensorFixedMetadataGroupIsCorrectlyNamed(self):
    #     self.assertIn("sensor_fixed_metadata", self.groups, msg="sensor_fixed_metadata should be a group in root level")
        
    # def testTheGantrySystemVariableMetadataGroupIsCorrectlyNamed(self):
    #     self.assertIn("gantry_system_variable_metadata", self.groups, msg="gantry_system_variable_metadata should be a group in root level")
        
    # def testTheUserGivenMetadataGroupIsCorrectlyNamed(self):
    #     self.assertIn("user_given_metadata", self.groups, msg="user_given_metadata should be a group in root level")
        
    # def testTheSensorVariableMetadataGroupIsCorrectlyNamed(self):
    #     self.assertIn("sensor_variable_metadata", self.groups, msg="gantry_system_fixed_metadata should be a group in root level")
        
    # def testTheHeaderInfoGroupIsCorrectlyNamed(self):
    #     self.assertIn("header_info", self.groups, msg="header_info should be a group in root level")

    def testWavelengthArrayHasEnoughData(self):
        '''
        Roughly check if there are enough numbers of wavelengths and compare their values
        '''
        self.wavelengthArray = self.masterNetCDFHandler.variables['wavelength']
        self.assertIn(len(self.wavelengthArray), (272, 273, 275, 939, 955), msg="The length of the wavelength is wrong")
    
    def testWavelengthArrayHasCorrectData(self):
        self.wavelengthArray = self.masterNetCDFHandler.variables['wavelength']

        self.assertGreater(self.wavelengthArray[0], 3e-7, msg="The first sample of the wavelength should greater than 300nm")
        self.assertLess(   self.wavelengthArray[0], 1e-6, msg="The last sample of the wavelength should greater than 1000nm")

    def testHistoryIsCorrectlyRecorded(self):
        '''
        Check if the product has a correct attribute called "history"
        '''
        self.assertTrue(getattr(self.masterNetCDFHandler, "history"), msg="The product must have an attribute called history")
        
        self.historyData = self.masterNetCDFHandler.history
        #self.assertRegexpMatches(self.historyData,
        #                         r'[a-zA-Z]{3}\s[a-zA-Z]{3}\s[\d]{1,2}\s[\d]{2}[:][\d]{2}[:][\d]{2}\s[\d]{4}[:]\spython\s.*',
        #                         msg="The history string should anyhow larger than 0")
    
    def testFrameTimeHasCorrectCalendarAttr(self):
        self.assertIn("frametime", self.masterNetCDFHandler.variables, msg="The calender should be in the root level")

        self.frameTime = self.masterNetCDFHandler.variables["frametime"]
        self.assertEqual(self.frameTime.calender, "gregorian", msg="The calender for frametime is gregorian")

    def testFrameTimeHasCorrectUnitsAttr(self): 
        self.frameTime = self.masterNetCDFHandler.variables["frametime"]       
        self.assertEqual(self.frameTime.units, "days since 1970-01-01 00:00:00", msg="The units for frametime should be based on Unix-basetime")

    def testFrameTimeHasCorrectValue(self): 
        self.frameTime = self.masterNetCDFHandler.variables["frametime"]       
        self.assertGreater(self.frameTime[0], 16000, msg="The value for frametime should anyhow larger than 16000")
    
    # def testRedBandIndexIsCorrectlyRecorded(self):
    #     '''
    #     Check if there are three band indices and their values are correct
    #     '''
    #     self.headerInformation = self.groups["header_info"]
    #     self.redIndex   = self.headerInformation.variables["red_band_index"]

    #     self.assertEqual(self.redIndex[...],   235, msg="The value of red_band_index is always 235")

    # def testBlueBandIndexIsCorrectlyRecorded(self):
    #     self.headerInformation = self.groups["header_info"]

    #     self.blueIndex  = self.headerInformation.variables["blue_band_index"]
    #     self.assertEqual(self.blueIndex[...],  141, msg="The value of blue_band_index is always 141")

    # def testGreenBandIndexIsCorrectlyRecorded(self):
    #     self.headerInformation = self.groups["header_info"]

    #     self.greenIndex = self.headerInformation.variables["green_band_index"]
    #     self.assertEqual(self.greenIndex[...], 501, msg="The value of green_band_index is always 501")

    # def testGreenBandIndexIsUnsignedShortInteger(self):
    #     self.headerInformation = self.groups["header_info"]

    #     self.greenIndex = self.headerInformation.variables["green_band_index"]
    #     self.assertEqual(self.greenIndex.dtype, "u2", msg="Indices must be saved as unsigned short integers")

    # def testBlueBandIndexIsUnsignedShortInteger(self):
    #     self.headerInformation = self.groups["header_info"]

    #     self.blueIndex = self.headerInformation.variables["blue_band_index"]
    #     self.assertEqual(self.blueIndex.dtype, "u2", msg="Indices must be saved as unsigned short integers")

    # def testRedBandIndexIsUnsignedShortInteger(self):
    #     self.headerInformation = self.groups["header_info"]

    #     self.redIndex = self.headerInformation.variables["red_band_index"]
    #     self.assertEqual(self.redIndex.dtype, "u2", msg="Indices must be saved as unsigned short integers")

    # def testXHaveCorrectValuesAndAttributes(self):
    #     '''
    #     Check if the georeferencing data are correct (for x and y)
    #     '''
    #     self.x = self.masterNetCDFHandler.variables["x"]
    #     self.assertEqual(len(self.x), 1600, msg="The width of the image should always be 1600 pxl")
    #     self.assertEqual(self.x.units, "meter", msg="The unit for x should always be meter")

    # def testYHaveCorrectValuesAndAttributes(self):
    #     '''
    #     Check if the georeferencing data are correct (for x and y)
    #     CHANGE the msg.
    #     '''
    #     self.y = self.masterNetCDFHandler.variables["y"]
    #     self.assertEqual(len(self.y), 169,  msg="The height of the image should always be 169 pxl")
    #     self.assertEqual(self.y.units, "meter", msg="The unit for y should always be meter")

    # def testPositionVariablesAreCorrectlyFormatted(self):
    #     self.variable_metadata = self.groups["gantry_system_variable_metadata"].variables
    #     self.assertIn("position_x", self.variable_metadata, msg="The position should be named as position x")

    #     self.assertEqual(self.variable_metadata["position_x"].units, "meter", msg="The position should has an unit of meter")
    #     self.assertEqual(self.variable_metadata["position_x"].long_name, "Position in X Direction", msg="The position should has a correctly formatted long name")

    # def testSpeedVariablesAreCorrectlyFormatted(self):
    #     self.variable_metadata = self.groups["gantry_system_variable_metadata"].variables
    #     self.assertIn("speed_x", self.variable_metadata, msg="The position should be named as speed x")

    #     self.assertEqual(self.variable_metadata["speed_x"].units, "meter second-1", msg="The speed should has an unit of meter second-1")
    #     self.assertEqual(self.variable_metadata["speed_x"].long_name, "Gantry Speed in X Direction", msg="The speed should has a correctly formatted long name")

    # Marked as a parameterized testcases; will be executed several times
    def testXHasEnoughAttributes(self):
        self.x = self.masterNetCDFHandler.variables["x"]

        for potentialAttributes in ["units", "reference_point", "long_name", "algorithm"]:
            self.assertHasAttribute(self.x, potentialAttributes, msg="X has missing attributes")

    # Marked as a parameterized testcases; will be executed several times
    def testYHasEnoughAttributes(self):
        self.y = self.masterNetCDFHandler.variables["y"]
        
        for potentialAttributes in ["units", "reference_point", "long_name", "algorithm"]:
            self.assertHasAttribute(self.y, potentialAttributes, msg="Y has missing attributes")

    # Walk through the reflectance image and compare with the max.sat.exp. to see whether it is overexposured
    @unittest.expectedFailure
    def testCalibrationGraphIsOverReflected(self):
        self.graph = np.array(self.masterNetCDFHandler.variables["rfl_img"])
        result = (self.graph > MAXIMUM_PLANT_REFLECTANCE).any()
        self.assertFalse(result, msg="The graph is over reflected (i.e., has the pixel grater than the max. plant reflectance, now = "+\
                                      str(MAXIMUM_PLANT_REFLECTANCE)+" )")

    def testSolarZenithAngleInReseaonableRange(self):
        self.graph  = np.array(self.masterNetCDFHandler.variables["solar_zenith_angle"])
        result_over = (self.graph > 90).any()
        result_lower = (self.graph < 0).any()
        self.assertFalse(result_over and result_lower, msg="The graph is over reflected (i.e., has the pixel grater than the max. plant reflectance, now = "+\
                                      str(MAXIMUM_PLANT_REFLECTANCE)+" )")

    @unittest.expectedFailure
    def testCalibrationGraphIsOverExposured(self):
        self.graph = np.array(self.masterNetCDFHandler.variables["xps_img"])
        result = (self.graph > SATURATED_EXPOSURE).any()
        self.assertFalse(result, msg="The graph is over exposured (i.e., has the pixel grater than the default saturated exposure, now = "+\
                                      str(SATURATED_EXPOSURE)+" )")


if __name__ == "__main__":
    test_parser = argparse.ArgumentParser()
    test_parser.add_argument('input_file_path', type=str, nargs=1,
                             help='The path to the final output')
    test_parser.add_argument('verbosity', type=int, nargs='?', default=3,
                             help='The verbosity of the test report (from 1 <least verbose> to 3 <the most verbose>)')
    test_parser.add_argument('maximum_plant_reflectance', type=float, nargs='?', default=MAXIMUM_PLANT_REFLECTANCE,
                             help='The maximum plant reflectance that has physical meaning (default=0.6)')
    test_parser.add_argument('saturated_exposure', type=int, nargs='?', default=DEFAULT_SATURATED_EXPOSURE,
                             help='The maximum saturated exposure that has physical meaning (default=2^16-1)')

    args = test_parser.parse_args()

    TEST_FILE_DIRECTORY       = args.input_file_path[0]
    MAXIMUM_PLANT_REFLECTANCE = args.maximum_plant_reflectance
    DEFAULT_SATURATED_EXPOSURE= args.saturated_exposure
    testSuite   = unittest.TestLoader().loadTestsFromTestCase(HyperspectralWorkflowTest)
    runner      = unittest.TextTestRunner(verbosity=args.verbosity).run(testSuite)
    returnValue = runner.wasSuccessful()
    sys.exit(not returnValue)