import {StorageBackend} from "./StorageBackend";


export default class MetaDataManager {

	protected sourceUrl: (build: number|"latest", locale: string) => string;
	protected backend: StorageBackend;
	public locale: string = "enUS";
	public cached: boolean = null;
	public fetched: boolean = null;
	public fallback: boolean = null;


	constructor(sourceUrl: (build: number|"latest", locale: string) => string, backend: StorageBackend, locale?: string) {
		this.sourceUrl = sourceUrl;
		this.backend = backend;
		if (locale) {
			this.locale = locale;
		}
	}

	protected generateKey(build: number|"latest"): string {
		if (build === "latest") {
			throw new Error('Will not generate key for "latest" metadata');
		}
		return "hsjson_build-" + build + "_" + this.locale;
	}

	protected fetch(build: number|"latest", cb?: (data: any[]) => void, error?: () => void): void {
		let url = this.sourceUrl(build, this.locale);
		$.ajax(url, {
			type: "GET",
			dataType: "text",
			success: (data: any, textStatus: string, jqXHR: any) => {
				let result = JSON.parse(data);
				cb(result);
			},
			error: (jqXHR: any, textStatus: string, errorThrown: string) => {
				if (!jqXHR.status) {
					// request was probably cancelled
					return;
				}
				error();
			}
		});
	}

	protected has(build: number|"latest"): boolean {
		if (build === "latest") {
			return false;
		}
		return this.backend.has(this.generateKey(build));
	}

	public get(build: number|"latest", cb: (data: any[]) => void): void {
		if (!build || isNaN(+build)) {
			build = "latest";
		}
		this.cached = false;
		if (build !== "latest") {
			this.fetched = false;
			this.fallback = false;
			let key = this.generateKey(build);
			if (this.backend.has(key)) {
				this.cached = true;
				cb(this.backend.get(key));
				return;
			}
		}
		this.fetch(build, (data: any[]) => {
			this.fetched = true;
			if(!this.fallback) {
				this.fallback = false;
			}
			cb(data);
			if (build !== "latest") {
				this.backend.set(this.generateKey(build), data);
			}
		}, () => {
			if(build === "latest") {
				if(this.locale == "enUS") {
					// completely failed
					return;
				}
				else {
					this.locale = "enUS";
				}
			}
			// fallback to latest
			this.fallback = true;
			this.get("latest", cb);
		});
	}
}
