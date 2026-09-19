# What?
This small document is the starting point for the process of improving and continous evaluation of the artifacts generated. It will be used to document in an informal way the introduction of new features. The content of this document will be then used to write down a more formal document about the project.

This document is a kind of diary that has as goal:

_Critical evaluation and maintenance: Test, review, correct, and improve the generated artefacts; document how problems were discovered and verified._

# Features

## 1 - Data-corruption

The Entire system does not perform any kind of data validation through the entire pipeline, then the Cloud may end up receiving and storing every type of data (Corrupted due to a sensor malfunction or due to transmission problems over the network).

In order to avoid poisoning the database with "Wrong data" we need to modify and solve this issue we will proceed as follow:

* Expand the functionality of the Edge Gateway in order to drop the "bad packets".
* The Edge Gatway will keep a log of the discarded packets that can be checked.
* The Cloud Service rise an alarm of some kind if it do not recive update from the sensor for a long time.

We updated accordingly the test suite. We updated the test_baseline.py in order to verify only the happy path (zero failure rate) and we created a new test suites called test_failure_handling that only verifies the handling of corrupted packets.

While running the new test suite we discovered that some malformed packege are able to slip through, this because the legacy system relies on AES-CBC that does not provide any integrity guarantees. Since the Sensor is a legacy system and we cannot apply fixes here we must surrender to the idea that fixing this issue is impossible, but we can mitigate it:

First of all we can make the validation performed by the gateway more strinct in this way: istead checking only that the temperature is a float as the current implementation does we can enforce a regex. Another measure to reduce the probability that malformed records goes throw is to verify that the timestamp falls in a certain interval of time (depending on the network conditions and so on, we will just say some minutes for our examples). These measures won't catch corruption where 17.5
flips to 16.5 but will drastically reduce the number of undetected corruptions.

Then since have a 100% success rate is not feasible we must set a treshold for our tests. We say that we are satisfied (our test passes) if the system catches 95% of the malformed packets.

The probability of a message of passing throug depends also on the admitted time interval of the Edge Gateway, tighter is the interval, more probable is to spot corrupted package, if the interval is too tight good pachets may be discarded.

### The technical debt
Since the Communication between The sensor and the Gateway still relies on AES-CBC in this part of the system the information may be subject to tampering or networks error, this represent a security problem, related to the integrity of the information, that cannot be solved unless the Sensor itself is replaced. 

Moreover the time interval for withc the packet are accepted is another important element. See the last paragraph above for a description. This is also a techical debt problem of the system since we cannot safely catch all the bad packets

---

Moreover we previously implemented CR32 for checking the integirty of the communciation between the Edge Gateway and the Cloud Service. But this methods ensure integrity only against data-corruption in transit due to network problems, it is not a good method to check integrity for what concern intentional data tampering. For this reason the AES-CBC mechanism previously used has been substituted with a more robust AES-GCM able to enforce both confidentiality and cryptography, the 256-bit key enforce post-quantum resistence. Moreover AES-GCM ensure both integrity for what concern accidental tampering and intentional ones.

After this implementations the test suit is beign runned 100 times to ensure as much as statistical coverage as possible.


