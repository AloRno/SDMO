from mlkem.ml_kem import ML_KEM
from mlkem.parameter_set import ML_KEM_768

def test_mlkem():

    ml_kem = ML_KEM(parameters=ML_KEM_768)
    ek, dk = ml_kem.key_gen()
    shared_secret, ciphertext = ml_kem.encaps(ek)
    shared_secret_decaps = ml_kem.decaps(dk, ciphertext)

    assert shared_secret == shared_secret_decaps
    print("ML-KEM working!")
    print("EK type:", type(ek))
    print("EK length:", len(ek))
    print("Ciphertext type:", type(ciphertext))
    print("Ciphertext length:", len(ciphertext))
