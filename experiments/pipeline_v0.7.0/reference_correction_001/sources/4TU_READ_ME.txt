#Machine learning for the analysis of microscopy images of carbon composites 

These data sets are used to develop a deep learning model that is able to predict fibres, voids and matrix material in micrographs of cross sections of Carbon-fibre-reinforced polymers (CFRP).
The data was collected at the ThermoPlastic composites Research Center (TPRC) and consist of 256 x 256 pixel images made from digital microscopy images of cross sections of unidirectional layers of CFRPs. 

There are four folders containing the four main data sets:

* Data set I
* Data set II
* Data set III
* Test data set

Each folder, except the test data set, consist of the original data set with the images that are directly obtained from the original micrographs 
and the augmented data set, where the original images and masks are augmented using the following data augmention methods:

* Horizontal flip
* Vertical flip
* Random sized crop (crop size between 128 and 250 pixels)
* Random brightness (+/- 20%)
* Random contrast (+/- 20%)
* CLAHE (clip limit between 1 and 4, tile size 8 x 8)
* Gaussian blur (kernel size between 3 and 7)

Each of these transformations has a probability of 50% of happening to an image. 


Both sets contain a folder with the images and a folder with the segmentation masks.
The masks are annotated versions of the image where each pixel is labeled with the number 0, 1 and 2 corresponding to a class:

0 = matrix
1 = fibre
2 = void 

The masks are made using ImageJ. The centres of the fibres are found using a local maxima method and perfect circles with the average fibre radius are plotted around them. 
Voids are detected using a thresholding algorithm based on the mimium method. Note, that these masks are therefore not perfect. 


A short overview of the data sets can be found here. An elaborated overview can be found in the thesis when it will come availble online. 

* Data set I
This data set contains 500 images of which 405 contain voids. All images come from the same C/PEEK material and the fibres have an average radius of 3 pixels. 
 
* Data set II
This data set contains 500 images. 250 images come from data set I and thus have a fibre radius of 3 pixels and come from C/PEEK material. 204 of the 250 images contain voids.
The other 250 images come from a C/LM-PEAK material and have an avarage fibre radius of 10 pixels. However, these images do not contain voids.

* Data set III
This data set contains 1000 images of C/LM-PEAK and C/PEEK materials. 9 different fibre radii are present in this data set, namely: 2, 3, 4, 5, 6, 10, 11, 14 and 22 pixels. 
There are 100 images of each fibrer radius present in this data set. Except from radius 3, as there are 200 images containing fibres with an average radius of 3. 
In total 191 images of the 1000 images contain voids. 

* Test data set
This data set consist of 32 images. 16 images come from a C/LM-PEAK material with an average fibre radius of 7 pixels and 2 images with voids. 
The other 16 images come from a C/PEEK material with an average fibre radius of 7 pixels and 4 images with voids. 