import * as React from "react";

interface GameHistoryResultFilterProps extends React.ClassAttributes<GameHistoryResultFilterState > {
	setQuery: (type: string) => void;
	selected: string;
}

interface GameHistoryResultFilterState {
}

export default class GameHistoryResultFilter extends React.Component<GameHistoryResultFilterProps, GameHistoryResultFilterState> {

	render(): JSX.Element {
		if (!this.props.selected) {
			this.props.selected = "";
		}
		return (
			<div>
				<select className="form-control" onChange={(e: any) => this.props.setQuery(e.target.value)} value={this.props.selected}>
					<option value="">All Results</option>
					<option value="won">Won</option>
					<option value="lost">Lost</option>
				</select>
			</div>
		);
	}
}
