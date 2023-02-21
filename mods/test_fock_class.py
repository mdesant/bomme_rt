import os
import sys
import psi4
import numpy as np

sys.path.insert(0, "./common")
modpaths = os.environ.get('MODS_PATH')

if modpaths is not None :
    for path in modpaths.split(";"):
        sys.path.append(path)
from scf_run import run
from init_run import initialize

bset,bsetH, molelecule_str, psi4mol, wfn = initialize(False,'direct','3-21G','3-21G','../examples/2h2o/H2O1.xyz',\
                   '../examples/2h2o/H2O2.xyz','hf','hf',0)

mints = psi4.core.MintsHelper(bset)

S = np.array(mints.ao_overlap())
numbas = bset.nbf()

I_Size = (numbas**4) * 8.e-9
nbfA = bsetH.nbf()

#make U matrix
U = np.eye(numbas)
S11=S[:nbfA,:nbfA]
S11_inv=np.linalg.inv(S11)
S12 =S[:nbfA,nbfA:]
P=np.matmul(S11_inv,S12)
U[:nbfA,nbfA:]=-1.0*P

#S block orthogonal
Stilde= np.matmul(U.T,np.matmul(S,U))
# get the ERI 4 index tensor
numpy_memory = 1

if I_Size > numpy_memory:
    psi4.core.clean()
    raise Exception("Estimated memory utilization (%4.2f GB) " +\
            "exceeds numpy_memory limit of %4.2f GB." % (memory_footprint, numpy_memory))
#Get Eri (2-electron repulsion integrals)
I = np.array(mints.ao_eri())

from Fock_helper import jkfactory

testjk =jkfactory(bset,psi4mol,jknative=True,eri=I)

Cocc = np.array(wfn.Ca_subset('AO','OCC'))
J = testjk.J(Cocc,np.array(wfn.Da()))
K = testjk.K(Cocc,np.array(wfn.Da()) )
H = np.array(mints.ao_kinetic())+ np.array(mints.ao_potential())
F_ref = H+ (2.0*J-K)
F_check = np.array(wfn.Fa())
test = np.allclose(F_check,F_ref,atol=1.0e-12)
print("TEST Fock : PASSED ... %s\n" % test)

print("testing fock_helper class\n")
from Fock_helper import fock_factory

fockbase = fock_factory(testjk,H,S,funcname='hf',basisobj=bset)
Jtest = fock_factory.J(fockbase,Cocc,out=[[0,numbas],[0,numbas]])
Ktest = fock_factory.K(fockbase,Cocc)

test = np.allclose(Jtest,J,atol=1.0e-12)
print("TEST J mtx : PASSED ... %s\n" % test)
test = np.allclose(Ktest,K,atol=1.0e-12)
print("TEST K mtx : PASSED ... %s\n" % test)
print("Getting K mtx using get_xcpot")
xchf= fock_factory.get_xcpot(fockbase,'hf',bset,Cocc=Cocc)
test = np.allclose(Ktest,-1.0*xchf,atol=1.0e-12)
print("TEST K(get_xcpot) mtx : PASSED ... %s\n" % test)


print("trying GGA/Hybrid")
func = 'b3lyp'
bset,bsetH, molelecule_str, psi4mol, wfn = initialize(False,'direct','3-21G','3-21G','../examples/2h2o/H2O1.xyz',\
                   '../examples/2h2o/H2O2.xyz',func,func,0)
#refresh orbital and fockbase
Cocc = np.array(wfn.Ca_subset('AO','OCC'))
fockbase = fock_factory(testjk,H,S,funcname=func,basisobj=bset)
Vxc_mat = fock_factory.get_xcpot(fockbase,func,bset,Cocc=Cocc)

if func == 'hf':
  test = np.allclose(Ktest,-1.0*Vxc_mat,atol=1.0e-12)
  print("TEST Vxc_mat) mtx : PASSED ... %s\n" % test)
#refresh J
J = testjk.J(Cocc,np.array(wfn.Da()))
 
Test_H = H +2.00*J +Vxc_mat

test = np.allclose(np.array(wfn.Fa()),Test_H,atol=1.0e-12)
print("test GGA/hybrid Fock (sum of term): Passed .... %s\n" % test)

print("compute full fock straight away..")
Fnew = fockbase.get_Fock(Cocc)
test = np.allclose(Test_H,Fnew,atol=1.0e-12)
print("test GGA/hybrid gen Fock: Passed .... %s\n" % test)

