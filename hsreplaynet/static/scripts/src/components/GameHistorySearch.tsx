import * as React from "react";


interface GameHistorySearchProps extends React.ClassAttributes<GameHistorySearchState > {
	query: string;
	setQuery: (query: string) => void;
}

interface GameHistorySearchState {
}

export default class GameHistorySearch extends React.Component<GameHistorySearchProps, GameHistorySearchState> {

	render(): JSX.Element {
		if (!this.props.query) {
			this.props.query = "";
		}
		return (
			<div>
				<input
					type="search"
					placeholder="Search for players…"
					className="form-control"
					value={this.props.query}
					onChange={(e: any) => this.props.setQuery(e.target.value)}
				/>
			</div>
		);
	}
}
