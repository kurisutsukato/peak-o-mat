Scripting peak-o-mat
====================

This has to be written yet. In the meanwhile you may look at some scripting examples from an ipython session. All these examples rely on version 1.1.7 or younger of peak-o-mat.

`This one <scripting_from_scratch.html>`_ shows how to use peak-o-mat completely without the GUI.

`This here <batch_fitting.html>`_ is an example of how to batch fit a series of spectra. It loads the sample project file shipped with peak-o-mat and uses the model of plot 5, set 4 as base for consecutive fits of the other sets. Since the spectra are slowly varying between the first and the last one, in every loop we use the result of the previous fit as initial guess for the next one. The fit is restricted to the x-interval (240,330). The project containing the fitted spectra is saved to a new project file. 

This is a very convenient way of using peak-o-mat. Use the GUI to load, transform and clean a series of spectra, choose and fit a model to one of the spectra and write a script to do all the batch fitting.

The scripts can also be run from within the shell module and using the code editor available since version 1.1.7 of peak-o-mat. Use 'project' as reference to the project structure. The following code snippet shows how to walk through the project tree, printing the names of all existent plots and sets::

  for np,p in enumerate(project):
      for ns,s in enumerate(p):
          print np,p.name,ns,s.name

  0 fermi 0 noisy	
  1 step 0 raw.dat
  2 ruby calibration 0 ruby.dat
  2 ruby calibration 1 ruby2.dat
  3 exp 0 exp_clean.dat
  3 exp 1 exp_noise.dat
  4 neon lamp 0 calib.dat
  5 raman 0 1.89RBM.dat
  5 raman 1 1.90RBM.dat
  5 raman 2 1.91RBM.dat
  5 raman 3 1.92RBM.dat
  5 raman 4 1.93RBM.dat

Note: Whereever in the code you go back one indention level, i.e. at the end of a loop, you need to add an empty line. This is a limitation of the shell.

