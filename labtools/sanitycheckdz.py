# explaining every step of SyntheticSchlieren.  To understand the purpose of every single step and view the output of every step.


import Image
import numpy
import matplotlib.pyplot as plt
import SyntheticSchlieren as SS
import skimage.morphology, skimage.filter
from scipy import ndimage
# take a look at a time series of any single vertical column of the video
im = Image.open('/Users/prajvala/Documents/Project_labtools/labtools/plots/vtsVID764.png')
im = numpy.array(im)
plt.figure(1)
ax = plt.subplot(2,2,1)
plt.imshow(im,
           interpolation='nearest')
plt.title('vertical time series')
plt.colorbar()

# constants used in computing Synthetic Schlieren
min_tol = 7  # small mintol means you have more regions that are returned by getTOL function
sigma = 11
filter_size=10
video_id = 764
dz = 58.0/964
nz, nt = im.shape
disk_size = 4 # it will make a 9 by 9 array with a circular disk of 1's
plot_maxmin = 0.05

# getTOL returns a matrix that helps us capture only the motion that is monotonic in time.
# we only want to capture the motions of the black and white lines as that represents propagating internal waves.
C = SS.newGetTol(im, mintol = min_tol)
# take a look at the matrix returned by getTOL
#plt.figure()
plt.subplot(2,2,2,sharex=ax, sharey=ax)
plt.imshow(C,interpolation='nearest',
           )
plt.title('mintol')
plt.colorbar()

delz = numpy.zeros((nz,nt),dtype=numpy.float32)
# the compute_dz_image function return a dz array interspersed with nan's
for i in range(1,nt):
    array1 = im[:,i-1].reshape((-1,1))
    array2 = im[:,i].reshape((-1,1))

    #print array1.shape
    temp1 = SS.compute_dz_image(array1,
                                array2,
                                dz)
    delz[:,i] = temp1.reshape((964,))
# take a look at delz with nan's
#plt.figure()
plt.subplot(2,2,3, sharex=ax, sharey=ax)
plt.imshow(delz,
           vmax=plot_maxmin,vmin=-plot_maxmin,interpolation='nearest',

            )
plt.title('raw delz')
plt.colorbar()

# remove the nan's
delz = numpy.nan_to_num(delz)
# take a look at delz without nan's
plt.figure(2)
plt.imshow(delz,
           vmin = -plot_maxmin,vmax = plot_maxmin,interpolation='nearest',
           )
plt.title('delz after removing nan')
plt.colorbar()
# multiplying delz with C gives us delz that has only monotonically increasing motion which is what we want
delz = delz * C
# take a look at delz now! vmin and vmax are used to show you the actual dz values which are quite small

plt.figure(1)
plt.subplot(2,2,4, sharex=ax, sharey=ax)
plt.imshow(delz,
           vmax=plot_maxmin,vmin=-plot_maxmin,interpolation='nearest',
          )
plt.title('delz - monotonically increasing')
plt.colorbar()
# you'll notice that the values are very very high and that is because the function nan_to_num()
# replaces nan's with zeros and -infinity with very small values and +infinity with very large values
# So now we need to cut the very large and very small values off

# implementing the skimage.filter.mean so as to apply mean filter on a
# masked array and then applying a gaussian filter to smooth the image

# step 1: clip the large values
min_max = 0.05 # 0.05 cm dz per pixel shift is plenty!
clip_min_max = 0.95 * min_max # actual clipping value is 0.0475
delz[delz > clip_min_max] = clip_min_max # clipping the very large values
delz[delz < -clip_min_max] = -clip_min_max # clipping off the very small values
# take a look at the clipped delz
plt.figure()
plt.imshow(delz,interpolation='nearest')

plt.title('clipped delz')
plt.colorbar()
# Step 2 : map the original data from -0.05 to +0.05 to range from 0 to 255
check = numpy.array((delz + min_max/(2.0 *min_max)*256) ,dtype=numpy.uint8)
check1 = numpy.array(((delz + min_max)/(2.0 *min_max)*256),dtype=numpy.uint8)
print check[700:750,570:580], "\n######\n", check1[700:750,570:580]

# just found a bug in SyntheticSchlieren!!! previously the expression was delz + min_max/(.5 *min_max)*256 instead of being
#(delz + min_max)/(.5 *min_max)*256). In the first case the mapped_delz has only 0 and 255 instead of having a
# range of numbers
mapped_delz = numpy.uint8((delz + min_max)/ (2.0* min_max) * 256)
# take a look at mapped_delz
#print mapped_delz[700:750,570:580]
plt.figure(3)
ax  = plt.subplot(2,1,1)
plt.imshow(mapped_delz,interpolation='nearest')
plt.title('mapped delz')
plt.colorbar()
# Step 3 : prepare a mask:: 1 means use the data and 0 means ignore the
# data here within the disk
# The mask is 0 wherever the data is bad and 1 wherever the data is to be considered
mask_delz = numpy.uint8(mapped_delz <>128)
# take a look at the mask
plt.figure()
plt.imshow(mask_delz)
plt.title('mask_delz')
plt.colorbar()
#Step 4: apply the mean filter to compute values for the masked pixels
disk_size = 15 # this is the size of the disk used for the mean filter
print "delz.shape", delz.shape
nz,nt = delz.shape
row_disk = numpy.ones((disk_size,1))

filtmapped_delz = numpy.ones((nz,nt))
# This is better than applying a spatial filter in x and z .. atleast till we verify that it makes no significant difference
for i in range(0,nt-1):
    mdelz = numpy.reshape(mapped_delz[:,i], (nz,1))
    filt_delz = skimage.filter.rank.mean(mdelz,
                #skimage.morphology.disk(disk_size),
                row_disk,
                mask = numpy.reshape(mask_delz[:,i],(nz,1)),
                )
    filtmapped_delz[:,i] = filt_delz[:,0]

#setting the zeros in filtmapped_delz to 128
filtmapped_delz[filtmapped_delz ==0 ] = 128
#print skimage.morphology.disk(disk_size)
# take a look at the mask
plt.figure(3)
plt.subplot(2,1,2,sharex = ax, sharey=ax)
plt.imshow(filtmapped_delz,interpolation='nearest')
plt.title('filt_delz' )
plt.colorbar()

# Step 5: mapping back the values from 0 to 255 to its original values of
# -0.05 to 0.05
filtered_delz = (filtmapped_delz / 256.0) * (2.0 * min_max) - min_max
# take a look at the remapped delz
plt.figure()
ax = plt.subplot(2,2,1)
plt.imshow(filtered_delz, vmin = -.05,vmax = 0.05,interpolation='nearest')
plt.title('remapped_delz' )
plt.colorbar()

# Step 6: Replacing the elements that were already right in the beginning
filled_delz = (1.0-mask_delz) * filtered_delz + mask_delz * delz
# take a look at the filled delz
plt.subplot(2,2,2,sharex = ax ,sharey = ax)
plt.imshow(filled_delz, vmin = -.05,vmax = 0.05,interpolation='nearest')
plt.title('filled_delz' )
plt.colorbar()

smooth_filt_delz = skimage.filter.gaussian_filter(filled_delz,
            [sigma,1])

# take a look at the filled delz
plt.subplot(2,2,3,sharex = ax,sharey = ax)
plt.imshow(smooth_filt_delz,
          vmin = -.05,vmax = 0.05,interpolation='nearest'
          )
plt.title('smoothed filled_delz')
plt.colorbar()
final_dz = ndimage.uniform_filter(smooth_filt_delz,
                                    size=(1,6),
                                    )
plt.subplot(2,2,4,sharex = ax,sharey = ax)
plt.imshow(final_dz,
          vmin = -.05,vmax = 0.05,interpolation='nearest'
          )
plt.title(' final_dz')
plt.colorbar()


plt.show()
