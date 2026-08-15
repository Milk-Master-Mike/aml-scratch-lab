import {cleanup,fireEvent,render,screen} from "@testing-library/react";
import {afterEach,vi,test,expect} from "vitest";
import Home from "./page";
afterEach(()=>cleanup());
test("renders the Scenario Forge",()=>{vi.stubGlobal("fetch",vi.fn(()=>Promise.resolve({json:()=>Promise.resolve([])})));render(<Home/>);expect(screen.getByRole("heading",{name:/Scenario Forge/i})).toBeInTheDocument();expect(screen.getByRole("button",{name:/Inject Scenario/i})).toBeInTheDocument()});

test("opens the regression runner",()=>{vi.stubGlobal("fetch",vi.fn(()=>Promise.resolve({ok:true,json:()=>Promise.resolve([])})));render(<Home/>);fireEvent.click(screen.getByRole("button",{name:/Regression Runner/i}));expect(screen.getByRole("heading",{name:/Regression Runner/i})).toBeInTheDocument();expect(screen.getByRole("button",{name:/Run All Tests/i})).toBeInTheDocument();expect(screen.getByRole("button",{name:/Inject Known Defect/i})).toBeInTheDocument()});
