#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# @author: Manuel Guenther <Manuel.Guenther@idiap.ch>
# @date:   Thu Sep  6 09:01:32 CEST 2012
#
# Copyright (C) 2011-2012 Idiap Research Institute, Martigny, Switzerland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""This module provides the Database interface allowing the user to query the
FRGC database in the most obvious ways.
"""

from .models import get_list, get_mask, get_annotations, client_from_file, client_from_model, File

from .driver import Interface
interface = Interface()

import os

class Database(object):
  """The Database class reads the original XML lists and provides access
  using the common xbob.db API.
  """

  def __init__(self, base_dir = interface.frgc_database_directory()):
    self.m_base_dir = base_dir
    # check that the database directory exists
    if not os.path.exists(self.m_base_dir):
      raise ValueError("The database directory '%s' does not exist. Please choose the correct path, or correct the path in the Interface.frgc_database_directory() function of the xbob/db/frgc/driver.py file."%base_dir)

    self.m_groups  = ('world', 'dev')
    self.m_purposes = ('enrol', 'probe')
    self.m_protocols = ('2.0.1', '2.0.2', '2.0.4') # other protocols might be supported later.
    self.m_mask_types = ('maskI', 'maskII', 'maskIII') # usually, only maskIII (the most difficult one) is used.

  def __check_validity__(self, elements, description, possibilities, default=None):
    """Checks validity of user input data against a set of valid values"""
    if not elements:
      return default if default else possibilities
    if not isinstance(elements, list) and not isinstance(elements, tuple):
      return self.__check_validity__((elements,), description, possibilities, default)
    for k in elements:
      if k not in possibilities:
        raise RuntimeError, 'Invalid %s "%s". Valid values are %s, or lists/tuples of those' % (description, k, possibilities)
    return elements

  def __check_single__(self, element, description, possibilities):
    """Checks that the given element is part of the possibilities."""
    if not element:
      raise RuntimeError, 'Please select one element from %s for %s' % (possibilities, description)
    if isinstance(element,tuple) or isinstance (element,list):
      if len(element) > 1:
        raise RuntimeError, 'For %s, only single elements from %s are allowed' % (description, possibilities)
      element = element[0]
    if element not in possibilities:
      raise RuntimeError, 'The given %s "%s" is not allowed. Please choose one of %s' % (description, element, possibilities)


  def client_ids(self, groups=None, protocol=None, purposes=None, mask_type='maskIII'):
    """Returns a list of client ids for the specific query by the user.

    Keyword Parameters:

    groups
      One or several groups to which the models belong ('world', 'dev').

    protocol
      One or several of the GBU protocols ('2.0.1', '2.0.2, '2.0.4'),
      required only if one of the groups is 'dev'.

    purposes
      One or several groups for which files should be retrieved ('enrol', 'probe').
      Only used when the group is 'dev'·
      For some protocol/mask_type pairs, not all clients are used for enrollment / for probe.

    mask_type
      One of the mask types ('maskI', 'maskII', 'maskIII').

    Returns: A list containing all the client id's which have the given properties.
    """
    groups = self.__check_validity__(groups, "group", self.m_groups)

    retval = set()

    if 'world' in groups:
      for file in get_list(self.m_base_dir, 'world', protocol):
        retval.add(file.m_signature)

    if 'dev' in groups:
      # validity checks
      purposes = self.__check_validity__(purposes, "purpose", self.m_purposes)
      self.__check_single__(protocol, "protocol", self.m_protocols)
      self.__check_single__(mask_type, "mask type", self.m_mask_types)

      # take only those models/probes that are really required by the current mask
      mask = get_mask(self.m_base_dir, protocol, mask_type)

      if 'enrol' in purposes:
        files = get_list(self.m_base_dir, 'dev', protocol, purpose='enrol')
        for index in range(len(files)):
          # check if this model is used by the mask
          if (mask[:,index] > 0).any():
            retval.add(files[index].m_signature)

      if 'probe' in purposes:
        files = get_list(self.m_base_dir, 'dev', protocol, purpose='probe')
        for index in range(len(files)):
          # check if this probe is used by the mask
          if (mask[index,:] > 0).any():
            retval.add(files[index].m_signature)

    return sorted(list(retval))


  def model_ids(self, groups=None, protocol=None, mask_type='maskIII'):
    """Returns a set of model ids for the specific query by the user.

    The models are dependent on the protocol and the mask.
    Only those FRGC "target" files are returned that are required by the given mask!

    .. warning ::
      Clients, models, and files are not identical for the FRGC database!
      Model ids are neither client nor file id's, so please do not mix that up!

    Keyword Parameters:

    groups
      One or several groups to which the models belong ('world', 'dev').

    protocol
      One or several of the GBU protocols ('2.0.1', '2.0.2, '2.0.4'),
      required only if one of the groups is 'dev'.

    mask_type
      One of the mask types ('maskI', 'maskII', 'maskIII').

    Returns: A list containing all the model id's belonging to the given group.
    """
    groups = self.__check_validity__(groups, "group", self.m_groups)
    # for models, purpose is always 'enrol'
    purpose = 'enrol'

    retval = set()
    if 'world' in groups:
      for file in get_list(self.m_base_dir, 'world'):
        retval.add(file.m_model)

    if 'dev' in groups:
      self.__check_single__(protocol, "protocol", self.m_protocols)
      self.__check_single__(mask_type, "mask type", self.m_mask_types)
      files = get_list(self.m_base_dir, 'dev', protocol, purpose)
      # take only those models that are really required by the current mask
      mask = get_mask(self.m_base_dir, protocol, mask_type)
      for index in range(len(files)):
        if (mask[:,index] > 0).any():
          retval.add(files[index].m_model)

    return sorted(list(retval))


  def get_client_id_from_model_id(self, model_id):
    """Returns the client_id attached to the given model_id.

    Keyword Parameters:

    model_id
      The model_id to consider

      .. warning ::
        The given model_id must have been the result of a previous call (models(), files())
        to the SAME database object, otherwise it will not be known or might be corrupted.

    Returns: The client_id attached to the given model_id
    """
    return client_from_model(model_id)


  def get_client_id_from_file_id(self, file_id):
    """Returns the client_id (real client id) attached to the given file_id

    Keyword Parameters:

    file_id
      The file_id to consider

      .. warning ::
        The given client_id must have been the result of a previous call (clients(), files())
        to the SAME database object, otherwise it will not be known.


    Returns: The client_id attached to the given file_id
    """
    return client_from_file(file_id)


  def objects(self, groups=None, protocol=None, purposes=None, model_ids=None, mask_type='maskIII'):
    """Using the specified restrictions, this function returns a list of File objects.

    Keyword Parameters:

    groups
      One or several groups to which the models belong ('world', 'dev').
      'world' files are "Training", whereas 'dev' files are "Target" and/or "Query".

    protocol
      One of the FRGC protocols ('2.0.1', '2.0.2', '2.0.4').
      Needs to be specified, when 'dev' is amongst the groups.

    purposes
      One or several groups for which files should be retrieved ('enrol', 'probe').
      Only used when the group is 'dev'·
      In FRGC terms, 'enrol' is "Target", while 'probe' is "Target" (protocols '2.0.1' and '2.0.2') or "Query" (protocol '2.0.4')

    model_ids
      If given (as a list of model id's or a single one), only the files
      belonging to the specified model id is returned.

      .. warning ::
        When querying objects of group 'world', model ids are expected to be client ids (as returned by 'client_ids()'),
        whereas for group 'dev' model ids are real model ids (as returned by 'model_ids()')

    mask_type
      One of the mask types ('maskI', 'maskII', 'maskIII').
    """
    def extend_file_list(file_list, frgc_file):
      """Extends the given file list with File's created from the given FRGCFile."""
      file_list.extend([File(frgc_file.m_signature, presentation, frgc_file.m_files[presentation]) for presentation in frgc_file.m_files])

    # check that every parameter is as expected
    groups = self.__check_validity__(groups, "group", self.m_groups)

    if isinstance(model_ids, int):
      model_ids = (model_ids,)

    retval = []

    if 'world' in groups:
      # extract training files
      for file in get_list(self.m_base_dir, 'world'):
        if not model_ids or file.m_signature in model_ids:
          for id, path in file.m_files.items():
            extend_file_list(retval, file)

    if 'dev' in groups:
      # check protocol, mask, and purposes only in group dev
      self.__check_single__(protocol, "protocol", self.m_protocols)
      self.__check_single__(mask_type, "mask type", self.m_mask_types)
      purposes = self.__check_validity__(purposes, "purpose", self.m_purposes)

      # extract dev files
      if 'enrol' in purposes:
        model_files = get_list(self.m_base_dir, 'dev', protocol, 'enrol')
        # return only those files that are required by the given protocol
        mask = get_mask(self.m_base_dir, protocol, mask_type)
        for model_index in range(len(model_files)):
          model = model_files[model_index]
          if not model_ids or model.m_model in model_ids:
            # test if the model is used by this mask
            if (mask[:,model_index] > 0).any():
              extend_file_list(retval, model)

      if 'probe' in purposes:
        probe_files = get_list(self.m_base_dir, 'dev', protocol, 'probe')
        # assure that every probe file is returned only once
        probe_indices = range(len(probe_files))

        # select only that files that belong to the models of with the given ids,
        # or to any model if no model id is specified
        model_files = get_list(self.m_base_dir, 'dev', protocol, 'enrol')
        mask = get_mask(self.m_base_dir, protocol, mask_type)

        for model_index in range(len(model_files)):
          model = model_files[model_index]
          if not model_ids or model.m_model in model_ids:
            probe_indices_for_this_model = probe_indices[:]
            for probe_index in probe_indices_for_this_model:
              if mask[probe_index, model_index]:
                extend_file_list(retval, probe_files[probe_index])
                probe_indices.remove(probe_index)

    return retval


  def annotations(self, file_id):
    """Returns the annotations for the given file id as a dictionary {'reye':(y,x), 'leye':(y,x), 'mouth':(y,x), 'nose':(y,x)}."""
    return get_annotations(self.m_base_dir, file_id)
