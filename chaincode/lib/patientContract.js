'use strict';

const { Contract } = require('fabric-contract-api');
const crypto = require('crypto');

class PatientContract extends Contract {

    constructor() {
        super('PatientContract');
    }

    async initLedger(ctx) {
        console.log('Patient ledger initialized');
    }

    /**
     * Registra un paciente en la blockchain.
     * No se guardan datos sensibles directamente, solo un hash + metadata de auditoría.
     */
    async createPatient(ctx, patientId, sapId, firstName, lastName, birthDate, gender, tipoEmpadronamiento, fechaInicio, dataHash) {
        const exists = await this._assetExists(ctx, `PATIENT_${patientId}`);
        if (exists) {
            throw new Error(`El paciente con ID ${patientId} ya existe en la blockchain`);
        }

        const patient = {
            docType: 'patient',
            patientId,
            sapId,
            firstName,
            lastName,
            birthDate,
            gender,
            tipoEmpadronamiento,
            fechaInicio,
            dataHash,
            createdAt: new Date().toISOString(),
            createdBy: ctx.clientIdentity.getID(),
        };

        await ctx.stub.putState(
            `PATIENT_${patientId}`,
            Buffer.from(JSON.stringify(patient))
        );

        ctx.stub.setEvent('PatientCreated', Buffer.from(JSON.stringify({
            patientId,
            sapId,
            timestamp: patient.createdAt,
        })));

        return JSON.stringify(patient);
    }

    /**
     * Actualiza datos de un paciente existente.
     * Queda registrado en el historial inmutable del ledger.
     */
    async updatePatient(ctx, patientId, updatedFieldsJson) {
        const key = `PATIENT_${patientId}`;
        const exists = await this._assetExists(ctx, key);
        if (!exists) {
            throw new Error(`El paciente con ID ${patientId} no existe`);
        }

        const currentData = await ctx.stub.getState(key);
        const patient = JSON.parse(currentData.toString());
        const updates = JSON.parse(updatedFieldsJson);

        const updatedPatient = {
            ...patient,
            ...updates,
            updatedAt: new Date().toISOString(),
            updatedBy: ctx.clientIdentity.getID(),
        };

        await ctx.stub.putState(key, Buffer.from(JSON.stringify(updatedPatient)));

        ctx.stub.setEvent('PatientUpdated', Buffer.from(JSON.stringify({
            patientId,
            timestamp: updatedPatient.updatedAt,
        })));

        return JSON.stringify(updatedPatient);
    }

    /**
     * Consulta un paciente por ID.
     */
    async queryPatient(ctx, patientId) {
        const data = await ctx.stub.getState(`PATIENT_${patientId}`);
        if (!data || data.length === 0) {
            throw new Error(`Paciente ${patientId} no encontrado`);
        }
        return data.toString();
    }

    /**
     * Devuelve el historial completo de cambios de un paciente.
     * Cada entrada tiene txId, timestamp y el estado en ese momento.
     * Ideal para auditorías.
     */
    async getPatientHistory(ctx, patientId) {
        const key = `PATIENT_${patientId}`;
        const iterator = await ctx.stub.getHistoryForKey(key);
        const history = [];

        while (true) {
            const res = await iterator.next();
            if (res.value) {
                const entry = {
                    txId: res.value.txId,
                    timestamp: res.value.timestamp,
                    isDelete: res.value.isDelete,
                };
                if (!res.value.isDelete) {
                    entry.value = JSON.parse(res.value.value.toString());
                }
                history.push(entry);
            }
            if (res.done) {
                await iterator.close();
                break;
            }
        }

        return JSON.stringify(history);
    }

    /**
     * Busca todos los pacientes por tipo de empadronamiento.
     */
    async queryPatientsByTipo(ctx, tipoEmpadronamiento) {
        const queryString = JSON.stringify({
            selector: {
                docType: 'patient',
                tipoEmpadronamiento,
            },
        });

        const iterator = await ctx.stub.getQueryResult(queryString);
        const results = [];

        while (true) {
            const res = await iterator.next();
            if (res.value) {
                results.push(JSON.parse(res.value.value.toString()));
            }
            if (res.done) {
                await iterator.close();
                break;
            }
        }

        return JSON.stringify(results);
    }

    async _assetExists(ctx, key) {
        const data = await ctx.stub.getState(key);
        return !!data && data.length > 0;
    }
}

module.exports = PatientContract;
