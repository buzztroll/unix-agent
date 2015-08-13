.. raw:: latex
  
      \newpage

.. _agent_installation:

Installation
------------

   The DCM Agent is distributed in either **rpm** or **deb** formation, however to ease in the installation a script is provided that will determine what package your server needs, download it, install it, and configure the system for use with it.

   There are 2 ways to install the DCM Agent using this script:

   1. **Interactive mode** - you are prompted for a subset of the available installation options. This is a good option for users who are new to the DCM Agent and want a guided installation process.

   2. **Non-interactive mode** - you specify the desired options as command line arguments. This is a good option for those that are automating the installation process. Note that non-interactive mode can be used in combination with "user data" or "startup scripts" on some clouds.

   In addition there are optional environment variables that you can set prior to installing the DCM Agent which affect and direct the installation and allow further custom installs.

   .. note:: Installing the DCM Agent requires **root** authority.

.. toctree::
   :titlesonly:

   agent_install_syntax
   agent_interactive_install
   agent_noninteractive_install
   agent_installation_env_variables
   agent_manual_install
