'use strict';

const { Contract } = require('fabric-contract-api');

class EnrollmentContract extends Contract {

    constructor() {
        super('EnrollmentContract');
    }

    async initLedger(ctx) {
        console.log('Enrollment ledger initialized');
    }

    /**
     * Registra un empadronamiento en la blockchain.
     * Vincula paciente + medicamentos + diagnóstico con un código único.
     */
    async createEnrollment(ctx, enrollmentId, enrollmentCode, patientId, tipo, medications, diagnostico, dataHash) {
        const exists = await this._assetExists(ctx, `ENROLLMENT_${enrollmentId}`);
        if (exists) {
            throw new Error(`El empadronamiento ${enrollmentId} ya existe`);
        }

        const patientExists = await this._assetExists(ctx, `PATIENT_${patientId}`);
        if (!patientExists) {
            throw new Error(`El paciente ${patientId} no existe. Debe registrarse primero.`);
        }

        const enrollment = {
            docType: 'enrollment',
            enrollmentId,
            enrollmentCode,
            patientId,
            tipo,
            medications: JSON.parse(medications),
            diagnostico,
            dataHash,
            status: 'ACTIVE',
            createdAt: new Date().toISOString(),
            createdBy: ctx.clientIdentity.getID(),
        };

        await ctx.stub.putState(
            `ENROLLMENT_${enrollmentId}`,
            Buffer.from(JSON.stringify(enrollment))
        );

        ctx.stub.setEvent('EnrollmentCreated', Buffer.from(JSON.stringify({
            enrollmentId,
            enrollmentCode,
            patientId,
            timestamp: enrollment.createdAt,
        })));

        return JSON.stringify(enrollment);
    }

    /**
     * Cambia el estado de un empadronamiento (ACTIVE, SUSPENDED, CANCELLED).
     */
    async updateEnrollmentStatus(ctx, enrollmentId, newStatus, reason) {
        const key = `ENROLLMENT_${enrollmentId}`;
        const exists = await this._assetExists(ctx, key);
        if (!exists) {
            throw new Error(`Empadronamiento ${enrollmentId} no encontrado`);
        }

        const validStatuses = ['ACTIVE', 'SUSPENDED', 'CANCELLED'];
        if (!validStatuses.includes(newStatus)) {
            throw new Error(`Estado inválido: ${newStatus}. Válidos: ${validStatuses.join(', ')}`);
        }

        const currentData = await ctx.stub.getState(key);
        const enrollment = JSON.parse(currentData.toString());

        enrollment.status = newStatus;
        enrollment.statusReason = reason;
        enrollment.statusUpdatedAt = new Date().toISOString();
        enrollment.statusUpdatedBy = ctx.clientIdentity.getID();

        await ctx.stub.putState(key, Buffer.from(JSON.stringify(enrollment)));

        ctx.stub.setEvent('EnrollmentStatusChanged', Buffer.from(JSON.stringify({
            enrollmentId,
            oldStatus: enrollment.status,
            newStatus,
            reason,
            timestamp: enrollment.statusUpdatedAt,
        })));

        return JSON.stringify(enrollment);
    }

    /**
     * Consulta un empadronamiento por ID.
     */
    async queryEnrollment(ctx, enrollmentId) {
        const data = await ctx.stub.getState(`ENROLLMENT_${enrollmentId}`);
        if (!data || data.length === 0) {
            throw new Error(`Empadronamiento ${enrollmentId} no encontrado`);
        }
        return data.toString();
    }

    /**
     * Devuelve todos los empadronamientos de un paciente.
     */
    async queryEnrollmentsByPatient(ctx, patientId) {
        const queryString = JSON.stringify({
            selector: {
                docType: 'enrollment',
                patientId,
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

    /**
     * Historial completo de un empadronamiento para auditoría.
     */
    async getEnrollmentHistory(ctx, enrollmentId) {
        const key = `ENROLLMENT_${enrollmentId}`;
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

    async _assetExists(ctx, key) {
        const data = await ctx.stub.getState(key);
        return !!data && data.length > 0;
    }
}

module.exports = EnrollmentContract;
