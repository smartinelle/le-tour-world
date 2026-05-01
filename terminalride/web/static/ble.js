/**
 * Web Bluetooth BLE Client for le-tour
 * 
 * Provides browser-based Bluetooth connectivity for FTMS trainers
 * and Heart Rate monitors. This replaces the Python bleak-based
 * BLE code for multi-user web deployments.
 * 
 * Browser Support: Chrome, Edge, Opera (NOT Safari or Firefox)
 */

// =============================================================================
// UUIDs
// =============================================================================

const UUIDS = {
    // Fitness Machine Service (FTMS)
    FTMS_SERVICE: '00001826-0000-1000-8000-00805f9b34fb',
    INDOOR_BIKE_DATA: '00002ad2-0000-1000-8000-00805f9b34fb',
    FTMS_CONTROL_POINT: '00002ad9-0000-1000-8000-00805f9b34fb',
    FTMS_STATUS: '00002ada-0000-1000-8000-00805f9b34fb',

    // Heart Rate Service
    HR_SERVICE: '0000180d-0000-1000-8000-00805f9b34fb',
    HR_MEASUREMENT: '00002a37-0000-1000-8000-00805f9b34fb',

    // Device Information
    DEVICE_INFO_SERVICE: '0000180a-0000-1000-8000-00805f9b34fb',
    MANUFACTURER_NAME: '00002a29-0000-1000-8000-00805f9b34fb',
    MODEL_NUMBER: '00002a24-0000-1000-8000-00805f9b34fb',
};

// =============================================================================
// FTMS Client
// =============================================================================

class FTMSClient {
    /**
     * Create a new FTMS client for trainer communication.
     * @param {Function} onData - Callback for incoming bike data
     * @param {Function} onStatus - Callback for connection status changes
     */
    constructor(onData, onStatus = null) {
        this.device = null;
        this.server = null;
        this.controlPoint = null;
        this.onData = onData;
        this.onStatus = onStatus || (() => { });
        this._isConnected = false;
    }

    get isConnected() {
        return this._isConnected && this.device?.gatt?.connected;
    }

    get deviceName() {
        return this.device?.name || 'Unknown Trainer';
    }

    /**
     * Request and select an FTMS device.
     * Opens the browser's Bluetooth pairing dialog.
     */
    async scan() {
        try {
            this.onStatus('scanning');

            this.device = await navigator.bluetooth.requestDevice({
                filters: [{ services: [UUIDS.FTMS_SERVICE] }],
                optionalServices: [
                    UUIDS.FTMS_SERVICE,
                    UUIDS.DEVICE_INFO_SERVICE
                ]
            });

            // Listen for disconnection
            this.device.addEventListener('gattserverdisconnected', () => {
                this._isConnected = false;
                this.onStatus('disconnected');
            });

            return {
                name: this.device.name,
                id: this.device.id
            };
        } catch (error) {
            this.onStatus('scan_failed');
            console.error('FTMS scan failed:', error);
            throw error;
        }
    }

    /**
     * Connect to the selected FTMS device.
     */
    async connect() {
        if (!this.device) {
            throw new Error('No device selected. Call scan() first.');
        }

        try {
            this.onStatus('connecting');

            this.server = await this.device.gatt.connect();
            const service = await this.server.getPrimaryService(UUIDS.FTMS_SERVICE);

            // Subscribe to Indoor Bike Data notifications
            const bikeDataChar = await service.getCharacteristic(UUIDS.INDOOR_BIKE_DATA);
            await bikeDataChar.startNotifications();
            bikeDataChar.addEventListener('characteristicvaluechanged', (event) => {
                const data = this._parseIndoorBikeData(event.target.value);
                this.onData(data);
            });

            // Get control point for ERG/SIM modes (optional)
            try {
                this.controlPoint = await service.getCharacteristic(UUIDS.FTMS_CONTROL_POINT);
                console.log('FTMS Control Point available');
            } catch (e) {
                console.warn('FTMS Control Point not available:', e.message);
            }

            this._isConnected = true;
            this.onStatus('connected');

            return true;
        } catch (error) {
            this.onStatus('connection_failed');
            console.error('FTMS connection failed:', error);
            throw error;
        }
    }

    /**
     * Scan and connect in one step.
     */
    async scanAndConnect() {
        await this.scan();
        return await this.connect();
    }

    /**
     * Parse Indoor Bike Data characteristic value.
     * Based on FTMS specification section 4.9.
     * 
     * @param {DataView} dataView - Raw characteristic data
     * @returns {Object} Parsed bike metrics
     */
    _parseIndoorBikeData(dataView) {
        const flags = dataView.getUint16(0, true);
        let offset = 2;

        const result = {
            timestamp: Date.now(),
            instantSpeed: null,     // km/h
            averageSpeed: null,     // km/h
            instantCadence: null,   // rpm
            averageCadence: null,   // rpm
            totalDistance: null,    // meters
            instantPower: null,     // watts
            averagePower: null,     // watts
            heartRate: null,        // bpm
            elapsedTime: null,      // seconds
            remainingTime: null,    // seconds
        };

        // Bit 0: More Data (0 = speed present)
        if (!(flags & 0x01)) {
            result.instantSpeed = dataView.getUint16(offset, true) * 0.01;
            offset += 2;
        }

        // Bit 1: Average Speed
        if (flags & 0x02) {
            result.averageSpeed = dataView.getUint16(offset, true) * 0.01;
            offset += 2;
        }

        // Bit 2: Instantaneous Cadence
        if (flags & 0x04) {
            result.instantCadence = dataView.getUint16(offset, true) * 0.5;
            offset += 2;
        }

        // Bit 3: Average Cadence
        if (flags & 0x08) {
            result.averageCadence = dataView.getUint16(offset, true) * 0.5;
            offset += 2;
        }

        // Bit 4: Total Distance (24-bit)
        if (flags & 0x10) {
            result.totalDistance = (
                dataView.getUint8(offset) |
                (dataView.getUint8(offset + 1) << 8) |
                (dataView.getUint8(offset + 2) << 16)
            );
            offset += 3;
        }

        // Bit 5: Resistance Level
        if (flags & 0x20) {
            offset += 2; // Skip, not commonly used
        }

        // Bit 6: Instantaneous Power
        if (flags & 0x40) {
            result.instantPower = dataView.getInt16(offset, true);
            offset += 2;
        }

        // Bit 7: Average Power
        if (flags & 0x80) {
            result.averagePower = dataView.getInt16(offset, true);
            offset += 2;
        }

        // Bit 8: Expended Energy (not commonly used)
        if (flags & 0x100) {
            offset += 5; // Skip
        }

        // Bit 9: Heart Rate
        if (flags & 0x200) {
            result.heartRate = dataView.getUint8(offset);
            offset += 1;
        }

        // Bit 10: Metabolic Equivalent (skip)
        if (flags & 0x400) {
            offset += 1;
        }

        // Bit 11: Elapsed Time
        if (flags & 0x800) {
            result.elapsedTime = dataView.getUint16(offset, true);
            offset += 2;
        }

        // Bit 12: Remaining Time
        if (flags & 0x1000) {
            result.remainingTime = dataView.getUint16(offset, true);
            offset += 2;
        }

        return result;
    }

    /**
     * Set target power for ERG mode.
     * @param {number} watts - Target power in watts (0-4094)
     */
    async setTargetPower(watts) {
        if (!this.controlPoint) {
            throw new Error('Control Point not available');
        }

        watts = Math.max(0, Math.min(4094, Math.round(watts)));

        const command = new Uint8Array([
            0x05, // Set Target Power opcode
            watts & 0xFF,
            (watts >> 8) & 0xFF
        ]);

        await this.controlPoint.writeValue(command);
        console.log(`Set target power: ${watts}W`);
    }

    /**
     * Set simulation grade for SIM mode.
     * @param {number} gradePercent - Grade percentage (-100% to +100%)
     * @param {number} crr - Coefficient of rolling resistance (default: 0.0045)
     * @param {number} cw - Wind resistance coefficient (default: 0.51)
     */
    async setSimGrade(gradePercent, crr = 0.0045, cw = 0.51) {
        if (!this.controlPoint) {
            throw new Error('Control Point not available');
        }

        // Grade: sint16, 0.01% resolution, range -100% to +100%
        const gradeValue = Math.round(gradePercent * 100);
        const clampedGrade = Math.max(-10000, Math.min(10000, gradeValue));

        // CRR: uint8, 0.0001 resolution
        const crrValue = Math.round(crr * 10000);

        // CW: uint8, 0.01 resolution
        const cwValue = Math.round(cw * 100);

        const command = new Uint8Array([
            0x11, // Set Indoor Bike Simulation Parameters opcode
            0x00, // Wind Speed (sint16) - low byte
            0x00, // Wind Speed - high byte
            clampedGrade & 0xFF,        // Grade - low byte
            (clampedGrade >> 8) & 0xFF, // Grade - high byte
            crrValue & 0xFF,            // CRR
            cwValue & 0xFF              // CW
        ]);

        await this.controlPoint.writeValue(command);
        console.log(`Set simulation: grade=${gradePercent}%, crr=${crr}, cw=${cw}`);
    }

    /**
     * Request control of the trainer (required before sending commands).
     */
    async requestControl() {
        if (!this.controlPoint) {
            throw new Error('Control Point not available');
        }

        const command = new Uint8Array([0x00]); // Request Control opcode
        await this.controlPoint.writeValue(command);
        console.log('Requested trainer control');
    }

    /**
     * Start the trainer.
     */
    async start() {
        if (!this.controlPoint) {
            throw new Error('Control Point not available');
        }

        const command = new Uint8Array([0x07]); // Start/Resume opcode
        await this.controlPoint.writeValue(command);
        console.log('Started trainer');
    }

    /**
     * Stop (pause) the trainer.
     */
    async stop() {
        if (!this.controlPoint) {
            throw new Error('Control Point not available');
        }

        const command = new Uint8Array([0x08, 0x01]); // Stop/Pause opcode, param=stop
        await this.controlPoint.writeValue(command);
        console.log('Stopped trainer');
    }

    /**
     * Disconnect from the trainer.
     */
    disconnect() {
        if (this.device?.gatt?.connected) {
            this.device.gatt.disconnect();
        }
        this._isConnected = false;
        this.device = null;
        this.server = null;
        this.controlPoint = null;
        this.onStatus('disconnected');
    }
}

// =============================================================================
// Heart Rate Client
// =============================================================================

class HeartRateClient {
    /**
     * Create a new Heart Rate client.
     * @param {Function} onData - Callback for heart rate data
     * @param {Function} onStatus - Callback for connection status changes
     */
    constructor(onData, onStatus = null) {
        this.device = null;
        this.server = null;
        this.onData = onData;
        this.onStatus = onStatus || (() => { });
        this._isConnected = false;
    }

    get isConnected() {
        return this._isConnected && this.device?.gatt?.connected;
    }

    get deviceName() {
        return this.device?.name || 'Unknown HR Monitor';
    }

    /**
     * Request and select a Heart Rate device.
     */
    async scan() {
        try {
            this.onStatus('scanning');

            this.device = await navigator.bluetooth.requestDevice({
                filters: [{ services: [UUIDS.HR_SERVICE] }]
            });

            this.device.addEventListener('gattserverdisconnected', () => {
                this._isConnected = false;
                this.onStatus('disconnected');
            });

            return {
                name: this.device.name,
                id: this.device.id
            };
        } catch (error) {
            this.onStatus('scan_failed');
            console.error('HR scan failed:', error);
            throw error;
        }
    }

    /**
     * Connect to the selected HR device.
     */
    async connect() {
        if (!this.device) {
            throw new Error('No device selected. Call scan() first.');
        }

        try {
            this.onStatus('connecting');

            this.server = await this.device.gatt.connect();
            const service = await this.server.getPrimaryService(UUIDS.HR_SERVICE);

            const hrChar = await service.getCharacteristic(UUIDS.HR_MEASUREMENT);
            await hrChar.startNotifications();
            hrChar.addEventListener('characteristicvaluechanged', (event) => {
                const data = this._parseHeartRate(event.target.value);
                this.onData(data);
            });

            this._isConnected = true;
            this.onStatus('connected');

            return true;
        } catch (error) {
            this.onStatus('connection_failed');
            console.error('HR connection failed:', error);
            throw error;
        }
    }

    /**
     * Scan and connect in one step.
     */
    async scanAndConnect() {
        await this.scan();
        return await this.connect();
    }

    /**
     * Parse Heart Rate Measurement characteristic.
     * Based on Bluetooth Heart Rate Profile specification.
     * 
     * @param {DataView} dataView - Raw characteristic data
     * @returns {Object} Parsed heart rate data
     */
    _parseHeartRate(dataView) {
        const flags = dataView.getUint8(0);
        let offset = 1;

        // Bit 0: Heart Rate Format
        let heartRate;
        if (flags & 0x01) {
            // 16-bit heart rate
            heartRate = dataView.getUint16(offset, true);
            offset += 2;
        } else {
            // 8-bit heart rate
            heartRate = dataView.getUint8(offset);
            offset += 1;
        }

        // Bits 1-2: Sensor Contact Status
        const sensorContactSupported = (flags & 0x04) !== 0;
        const sensorContact = sensorContactSupported && (flags & 0x02) !== 0;

        // Bit 3: Energy Expended Status
        let energyExpended = null;
        if (flags & 0x08) {
            energyExpended = dataView.getUint16(offset, true);
            offset += 2;
        }

        // Bit 4: RR-Interval
        const rrIntervals = [];
        if (flags & 0x10) {
            while (offset + 1 < dataView.byteLength) {
                // RR intervals in 1/1024 seconds
                const rr = dataView.getUint16(offset, true) / 1024 * 1000; // Convert to ms
                rrIntervals.push(rr);
                offset += 2;
            }
        }

        return {
            timestamp: Date.now(),
            heartRate,
            sensorContact,
            energyExpended,
            rrIntervals
        };
    }

    /**
     * Disconnect from the HR monitor.
     */
    disconnect() {
        if (this.device?.gatt?.connected) {
            this.device.gatt.disconnect();
        }
        this._isConnected = false;
        this.device = null;
        this.server = null;
        this.onStatus('disconnected');
    }
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Check if Web Bluetooth is supported in current browser.
 */
function isWebBluetoothSupported() {
    return 'bluetooth' in navigator;
}

/**
 * Get browser compatibility information.
 */
function getBrowserCompatibility() {
    const supported = isWebBluetoothSupported();
    const userAgent = navigator.userAgent;

    let browser = 'Unknown';
    if (userAgent.includes('Chrome')) browser = 'Chrome';
    else if (userAgent.includes('Edge')) browser = 'Edge';
    else if (userAgent.includes('Opera')) browser = 'Opera';
    else if (userAgent.includes('Firefox')) browser = 'Firefox';
    else if (userAgent.includes('Safari')) browser = 'Safari';

    return {
        supported,
        browser,
        message: supported
            ? `Web Bluetooth is supported in ${browser}`
            : `Web Bluetooth is NOT supported in ${browser}. Please use Chrome, Edge, or Opera.`
    };
}

// =============================================================================
// Export to global scope for NiceGUI integration
// =============================================================================

window.LeTourBLE = {
    FTMSClient,
    HeartRateClient,
    isWebBluetoothSupported,
    getBrowserCompatibility,
    UUIDS
};

console.log('LeTour BLE module loaded. Web Bluetooth supported:', isWebBluetoothSupported());
