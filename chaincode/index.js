'use strict';

const PatientContract = require('./lib/patientContract');
const EnrollmentContract = require('./lib/enrollmentContract');

module.exports.PatientContract = PatientContract;
module.exports.EnrollmentContract = EnrollmentContract;
module.exports.contracts = [PatientContract, EnrollmentContract];
