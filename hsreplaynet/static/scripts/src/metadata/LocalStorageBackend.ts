import {StorageBackend} from "./StorageBackend";


export default class LocalStorageBackend implements StorageBackend {

	private _available(): boolean {
		return typeof(Storage) !== "undefined";
	}

	public has(key: string): boolean {
		if (!this._available()) {
			return false;
		}
		return typeof(localStorage[key]) === "string";
	}

	public set(key: string, value: any): void {
		if (!this._available()) {
			return;
		}
		localStorage[key] = JSON.stringify(value);
	}

	public get(key: string): any {
		if (!this._available()) {
			return null;
		}
		return JSON.parse(localStorage[key]);
	}

}
